# Copyright (c) 2020 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt
# pylint: disable=undefined-variable
import os


# start multi-tenant settings override
DATABASES['default']['ENGINE'] = 'django_tenants.postgresql_backend'  # noqa: F821
DATABASE_ROUTERS = ['django_tenants.routers.TenantSyncRouter', ]


# attachments storage
DEFAULT_FILE_STORAGE = "tcms_tenants.storage.TenantFileSystemStorage"
MULTITENANT_RELATIVE_MEDIA_ROOT = "tenant/%s"


# this always needs to be the first app
if 'django_tenants' not in INSTALLED_APPS:      # noqa: F821
    INSTALLED_APPS.insert(0, 'django_tenants')  # noqa: F821


KIWI_TENANTS_DOMAIN = os.environ.get('KIWI_TENANTS_DOMAIN')


# TenantMainMiddleware always needs to be first
if 'django_tenants.middleware.main.TenantMainMiddleware' not in MIDDLEWARE:      # noqa: F821
    MIDDLEWARE.insert(0, 'django_tenants.middleware.main.TenantMainMiddleware')  # noqa: F821

if 'tcms_tenants.middleware.BlockUnauthorizedUserMiddleware' not in MIDDLEWARE:   # noqa: F821
    MIDDLEWARE.append('tcms_tenants.middleware.BlockUnauthorizedUserMiddleware')  # noqa: F821


TENANT_MODEL = "tcms_tenants.Tenant"
TENANT_DOMAIN_MODEL = "tcms_tenants.Domain"


# share login session between tenants
SESSION_COOKIE_DOMAIN = ".%s" % KIWI_TENANTS_DOMAIN


# everybody can access the main instance
SHARED_APPS = INSTALLED_APPS  # noqa: F821
