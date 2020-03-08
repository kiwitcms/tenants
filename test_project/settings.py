# pylint: disable=wildcard-import, unused-wildcard-import
# Copyright (c) 2019-2020 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt
# pylint: disable=invalid-name, protected-access, wrong-import-position
import os
import sys
import pkg_resources

# pretend this is a plugin during testing & development
# IT NEEDS TO BE BEFORE the wildcard import below !!!
dist = pkg_resources.Distribution(__file__)
entry_point = pkg_resources.EntryPoint.parse('kiwitcms_tenants_devel = tcms_tenants',
                                             dist=dist)
dist._ep_map = {'kiwitcms.plugins': {'kiwitcms_tenants_devel': entry_point}}
pkg_resources.working_set.add(dist)

from tcms.settings.product import *  # noqa: F403

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, BASE_DIR)


# these are enabled only for testing purposes
DEBUG = True
TEMPLATE_DEBUG = True
MEDIA_ROOT = os.path.join(BASE_DIR, 'uploads')
LOCALE_PATHS = [os.path.join(BASE_DIR, 'tcms_tenants', 'locale')]


# start multi-tenant settings override
DATABASES['default'].update({  # noqa: F405 pylint: disable=objects-update-used
    'ENGINE': 'django_tenants.postgresql_backend',
    'NAME': 'test_project',
    'USER': 'kiwi',
    'PASSWORD': 'kiwi',
    'HOST': 'localhost',
    'OPTIONS': {},
})

DATABASE_ROUTERS = [
    'django_tenants.routers.TenantSyncRouter',
]

MIDDLEWARE.insert(0, 'django_tenants.middleware.main.TenantMainMiddleware')   # noqa: F405
MIDDLEWARE.append('tcms_tenants.middleware.BlockUnauthorizedUserMiddleware')  # noqa: F405

TENANT_MODEL = "tcms_tenants.Tenant"
TENANT_DOMAIN_MODEL = "tcms_tenants.Domain"

# this always needs to be the first app
INSTALLED_APPS.insert(0, 'django_tenants')  # noqa: F405

TENANT_APPS = [
    'django.contrib.sites',

    'attachments',
    'django_comments',
    'modernrpc',
    'simple_history',

    'tcms.bugs',
    'tcms.core.contrib.linkreference',
    'tcms.management',
    'tcms.testcases.apps.AppConfig',
    'tcms.testplans.apps.AppConfig',
    'tcms.testruns.apps.AppConfig',
]

# everybody can access the main instance
SHARED_APPS = INSTALLED_APPS  # noqa: F405

# Allows serving non-public tenants on a sub-domain
# WARNING: doesn't work well when you have a non-standard port-number
KIWI_TENANTS_DOMAIN = 'tenants.localdomain'

# share login session between tenants
SESSION_COOKIE_DOMAIN = ".%s" % KIWI_TENANTS_DOMAIN

# attachments storage
DEFAULT_FILE_STORAGE = "tcms_tenants.storage.TenantFileSystemStorage"
MULTITENANT_RELATIVE_MEDIA_ROOT = "tenants/%s"
