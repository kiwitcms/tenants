# Copyright (c) 2019 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from django_tenants.utils import schema_context, tenant_context

from tcms_tenants.models import *


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


def create_tenant(name, schema_name, owner):
    with schema_context('public'):
        tenant = Tenant.objects.create(
            name=name,
            schema_name=schema_name,
            on_trial=True,
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
        site.save()

    return tenant
