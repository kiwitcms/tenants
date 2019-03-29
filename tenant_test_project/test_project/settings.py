# Copyright (c) 2019 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt

import os
import sys

from django.utils.translation import ugettext_lazy as _

from tcms.settings.product import *

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(BASE_DIR, os.pardir)))
sys.path.insert(0, BASE_DIR)

# these are enabled only for testing purposes
DEBUG = True
TEMPLATE_DEBUG = True

##### start multi-tenant settings override

DATABASES['default'].update({
    'ENGINE': 'django_tenants.postgresql_backend',
    'NAME': 'tenant_test_project',
    'USER': 'kiwi',
    'PASSWORD': 'kiwi',
    'HOST': 'localhost',
    'OPTIONS': {},
})

DATABASE_ROUTERS = [
    'django_tenants.routers.TenantSyncRouter',
]

MIDDLEWARE.insert(0, 'django_tenants.middleware.main.TenantMainMiddleware')
MIDDLEWARE.append('tcms_tenants.middleware.BlockUnauthorizedUserMiddleware')

TENANT_MODEL = "tcms_tenants.Tenant"
TENANT_DOMAIN_MODEL = "tcms_tenants.Domain"


INSTALLED_APPS.insert(0, 'django_tenants')
INSTALLED_APPS.insert(1, 'tcms_tenants')

TENANT_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.sites',

    'attachments',
    'django_comments',
    'modernrpc',
    'simple_history',

    'tcms.core.contrib.comments.apps.AppConfig',
    'tcms.core.contrib.linkreference',
    'tcms.management',
    'tcms.testcases.apps.AppConfig',
    'tcms.testplans.apps.AppConfig',
    'tcms.testruns.apps.AppConfig',
]

# because everybody can have access to the main instance
SHARED_APPS = INSTALLED_APPS

MENU_ITEMS.append(
    (_('TENANT'), [
        (_('Create'), '/not-implemented-yet/'),
        ('-', '-'),
        (_('Authorized users'), '/admin/tcms_tenants/tenant_authorized_users/'),
    ]),
)

# todo: enable later when we have views
# ROOT_URLCONF = 'dts_test_project.urls'
