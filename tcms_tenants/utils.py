# Copyright (c) 2019-2020 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt

import datetime
import uuid

from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from django_tenants.utils import schema_context, tenant_context
from tcms.kiwi_auth import forms as kiwi_auth_forms
from tcms.core.utils.mailto import mailto

from tcms_tenants.models import Domain, Tenant


UserModel = get_user_model()


def can_access(user, tenant):
    # everybody can access the public schema
    if tenant.schema_name == 'public':
        return True

    # anonymous users "can access" because they need to be able
    # to reach the login page
    if not user.is_authenticated:
        return True

    return tenant.authorized_users.filter(pk=user.pk).exists()


def owns_tenant(user, tenant):
    return tenant.schema_name != 'public' and \
            tenant.authorized_users.filter(pk=user.pk).exists()


def schema_name_not_used(name):
    if Tenant.objects.filter(schema_name=name).exists():
        raise ValidationError(_("Schema name already in use"))


# warning: doesn't play well when the domain has a port number
def tenant_domain(schema_name):
    return "%s.%s" % (schema_name, settings.KIWI_TENANTS_DOMAIN)


def tenant_url(request, schema_name):
    url = tenant_domain(schema_name)
    if request.is_secure:
        url = 'https://' + url
    else:
        url = 'http://' + url
    return url


def create_tenant(form_data, request):
    owner = request.user
    name = form_data['name']
    schema_name = form_data['schema_name'].lower()
    on_trial = form_data['on_trial']
    paid_until = form_data['paid_until']

    with schema_context('public'):
        tenant = Tenant.objects.create(
            name=name,
            schema_name=schema_name,
            paid_until=paid_until,
            on_trial=on_trial,
            owner=owner,
            organization=form_data['organization'],
        )
        domain = Domain.objects.create(
            domain=tenant_domain(schema_name),
            is_primary=True,
            tenant=tenant,
        )

        # work-around: for some reason the ContentType for tenant-user
        # relationship model doesn't get automatically created and if
        # the owner tries to add other authorized users via admin the
        # action will fail b/c ModelAdmin.log_addition tries to add a
        # a logging record linking to this content type and fails !
        ContentType.objects.get_for_model(tenant.authorized_users.through)

        # make the owner the first authorized user
        # otherwise they can't login
        tenant.authorized_users.add(owner)

    with tenant_context(tenant):
        # this is used to build full URLs for things like emails
        site = Site.objects.get(pk=settings.SITE_ID)
        site.domain = domain.domain
        site.name = domain.domain
        site.save()

    mailto(
        template_name='tcms_tenants/email/new.txt',
        recipients=[owner.email],
        subject=str(_('New Kiwi TCMS tenant created')),
        context={
            'tenant_url': tenant_url(request, tenant.schema_name),
        }
    )
    return tenant


def create_oss_tenant(owner, name, schema_name, organization):
    """
        Used to create tenants for our OSS program. Executed by the
        instance administrator!
    """
    class FakeRequest:  # pylint: disable=too-few-public-methods,nested-class-found
        is_secure = True
        user = None

        def __init__(self, username):
            self.user = UserModel.objects.get(username=username)

    data = {
        'name': name,
        'schema_name': schema_name.lower(),
        'organization': organization,
        'on_trial': False,
        'paid_until': datetime.datetime(2999, 12, 31),
    }

    request = FakeRequest(owner)

    return create_tenant(data, request)


# NOTE: defined here to avoid circular imports with forms.py
class RegistrationForm(kiwi_auth_forms.RegistrationForm):
    """
        Override captcha field b/c Kiwi TCMS may be configured to
        use reCAPTCHA and we don't want this to block automatic
        creation of user accounts!
    """
    captcha = None


def create_user_account(email_address):
    desired_username = username = email_address.split("@")[0]
    password = uuid.uuid4().hex

    i = 1
    while UserModel.objects.filter(username=username).exists():
        username = "%s.%d" % (desired_username, i)
        i += 1

    form = RegistrationForm(data={
        "username": username,
        "password1": password,
        "password2": password,
        "email": email_address,
    })

    user = form.save()

    # activate their account instead of sending them email with activation key
    user.is_active = True
    user.save()

    return user


def invite_users(request, email_addresses):
    for email in email_addresses:
        # note: users are on public_schema
        user = UserModel.objects.filter(email=email).first()

        # email not found, need to create account for them
        if not user:
            user = create_user_account(email)

        # user already authorized for tenant
        if request.tenant.authorized_users.filter(pk=user.pk).exists():
            continue

        request.tenant.authorized_users.add(user)
        mailto(
            template_name='tcms_tenants/email/invite_user.txt',
            recipients=[user.email],
            subject=str(_('Invitation to join Kiwi TCMS')),
            context={
                "invited_by": request.user.get_full_name() or request.user.username,
                "tenant_url": tenant_url(request, request.tenant.schema_name),
            }
        )
