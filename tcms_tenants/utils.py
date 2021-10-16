# Copyright (c) 2019-2021 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt

import datetime
import uuid

from django import forms
from django.conf import settings
from django.db import connections
from django.contrib.sites.models import Site
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from django_tenants.utils import (
    get_public_schema_name,
    get_tenant_database_alias,
    schema_context,
    tenant_context,
)
from tcms.kiwi_auth import forms as kiwi_auth_forms
from tcms.core.utils.mailto import mailto

from tcms_tenants.models import Domain, Tenant


UserModel = get_user_model()


def get_current_tenant():
    return connections[get_tenant_database_alias()].tenant


def can_access(user, tenant):
    # everybody can access the public schema
    if tenant.schema_name == get_public_schema_name():
        return True

    # everyone can access publicly readable tenants
    if tenant.publicly_readable:
        return True

    # anonymous users "can access" because they need to be able
    # to reach the login page
    if not user.is_authenticated:
        return True

    return tenant.authorized_users.filter(pk=user.pk).exists()


def owns_tenant(user, tenant):
    return tenant.schema_name != get_public_schema_name() and \
            tenant.authorized_users.filter(pk=user.pk).exists()


def schema_name_not_used(name):
    if Tenant.objects.filter(schema_name=name).exists():
        raise ValidationError(_("Schema name already in use"))


# warning: doesn't play well when the domain has a port number
def tenant_domain(schema_name):
    # take into account the fact that some customers deploy their 'public' schema
    # without a prefix, e.g. tcms.example.com == KIWI_TENANTS_DOMAIN or could use a
    # different domain for their tenant(s)!
    domain = Domain.objects.filter(tenant__schema_name=schema_name, is_primary=True).first()
    if domain:
        return domain.domain

    return f"{schema_name}.{settings.KIWI_TENANTS_DOMAIN}"


def tenant_url(request, schema_name):
    url = tenant_domain(schema_name)
    if request.is_secure:
        url = 'https://' + url
    else:
        url = 'http://' + url
    return url


def create_tenant(form, request):
    with schema_context('public'):
        # If a schema with name "empty" exists then use it for
        # cloning b/c that's faster
        if Tenant.objects.filter(schema_name='empty').first():
            schema_name = form.cleaned_data["schema_name"]
            paid_until = form.cleaned_data["paid_until"] or datetime.datetime(3000, 3, 31)
            call_command(
                "clone_tenant",
                "--clone_from", "empty",
                "--clone_tenant_fields", False,
                "--schema_name", schema_name,
                "--name", form.cleaned_data["name"],
                "--paid_until", paid_until,
                "--publicly_readable", form.cleaned_data["publicly_readable"],
                "--owner_id", request.user.pk,
                "--organization", form.cleaned_data["organization"] or "-",
                "--domain-domain", tenant_domain(schema_name),
                "--domain-is_primary", True,
            )
            tenant = Tenant.objects.get(schema_name=schema_name)
            if not form.cleaned_data["paid_until"]:
                tenant.paid_until = None
                tenant.save()

            if not form.cleaned_data["organization"]:
                tenant.organization = ""
                tenant.save()

            domain = tenant.domains.first()
        else:
            # otherwise default to applying all migrations one by one
            tenant = form.save()
            domain = Domain.objects.create(
                domain=tenant_domain(tenant.schema_name),
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
        tenant.authorized_users.add(tenant.owner)

    with tenant_context(tenant):
        # this is used to build full URLs for things like emails
        site = Site.objects.get(pk=settings.SITE_ID)
        site.domain = domain.domain
        site.name = domain.domain
        site.save()

    mailto(
        template_name='tcms_tenants/email/new.txt',
        recipients=[tenant.owner.email],
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

    class FakeTenantForm(forms.ModelForm):  # pylint: disable=nested-class-found
        class Meta:
            model = Tenant
            exclude = ("authorized_users",)  # pylint: disable=modelform-uses-exclude

    request = FakeRequest(owner)

    form = FakeTenantForm(initial={
        'owner': request.user.pk,
        'name': name,
        'schema_name': schema_name.lower(),
        'organization': organization,
        'publicly_readable': False,
        'paid_until': datetime.datetime(2999, 12, 31),
    })

    return create_tenant(form, request)


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
        username = f"{desired_username}.{i}"
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
