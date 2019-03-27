# Copyright (c) 2019 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt

import os
import sys

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
    'NAME': 'kiwitcms_test_project',
    'USER': 'kiwi',
    'PASSWORD': 'kiwi',
    'HOST': 'localhost',
})

DATABASE_ROUTERS = [
    'django_tenants.routers.TenantSyncRouter',
]

MIDDLEWARE.insert(0, 'tenant_tutorial.middleware.TenantTutorialMiddleware')

TENANT_MODEL = "tcms_tenants.Tenant"
TENANT_DOMAIN_MODEL = "tcms_tenants.Domain"


INSTALLED_APPS.insert(0, 'django_tenants')
INSTALLED_APPS.insert(1, 'tcms_tenants')

TENANT_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',

    'attachments',
    'django_comments',
    'modernrpc',
    'simple_history',

    'tcms.core',
    'tcms.kiwi_auth',
    'tcms.core.contrib.comments.apps.AppConfig',
    'tcms.core.contrib.linkreference',
    'tcms.management',
    'tcms.testcases.apps.AppConfig',
    'tcms.testplans.apps.AppConfig',
    'tcms.testruns.apps.AppConfig',
    'tcms.xmlrpc',
]

SHARED_APPS = [app for app in INSTALLED_APPS if not app in TENANT_APPS]

# todo: enable later when we have views
# ROOT_URLCONF = 'dts_test_project.urls'
