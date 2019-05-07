# Copyright (c) 2019 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt
# pylint: disable=too-many-ancestors
from datetime import datetime, timedelta

from django.conf import settings
from django.test import modify_settings
from django.http import HttpResponseForbidden

from tcms_tenants.tests import LoggedInTestCase


class BlockUnauthorizedUserMiddlewareTestCase(LoggedInTestCase):
    def test_unauthorized_user_cant_access_tenant(self):
        self.tenant.authorized_users.remove(self.tester)
        response = self.client.get('/')

        self.assertIsInstance(response, HttpResponseForbidden)
        self.assertIn('Unauthorized', str(response.content, encoding=settings.DEFAULT_CHARSET))


class BlockUnpaidTenantMiddlewareTestCase(LoggedInTestCase):

    @modify_settings(MIDDLEWARE={
        'append': 'tcms_tenants.middleware.BlockUnpaidTenantMiddleware',
    })
    def test_paid_until_is_none_access_forbidden(self):
        self.tenant.paid_until = None
        self.tenant.save()

        response = self.client.get('/')

        self.assertIsInstance(response, HttpResponseForbidden)
        self.assertIn('Unpaid', str(response.content, encoding=settings.DEFAULT_CHARSET))

    @modify_settings(MIDDLEWARE={
        'append': 'tcms_tenants.middleware.BlockUnpaidTenantMiddleware',
    })
    def test_paid_until_lt_today_access_forbidden(self):
        self.tenant.paid_until = datetime.now() - timedelta(days=1)
        self.tenant.save()

        response = self.client.get('/')

        self.assertIsInstance(response, HttpResponseForbidden)
        self.assertIn('Unpaid', str(response.content, encoding=settings.DEFAULT_CHARSET))

    @modify_settings(MIDDLEWARE={
        'append': 'tcms_tenants.middleware.BlockUnpaidTenantMiddleware',
    })
    def test_paid_until_expires_within_week_warning_shown(self):
        self.tenant.paid_until = datetime.now() + timedelta(days=3)
        self.tenant.save()

        response = self.client.get('/')

        self.assertContains(response, 'Tenant expires in less than 7 days')

    @modify_settings(MIDDLEWARE={
        'append': 'tcms_tenants.middleware.BlockUnpaidTenantMiddleware',
    })
    def test_paid_until_gt_today_access_granted(self):
        self.tenant.paid_until = datetime.now() + timedelta(days=30)
        self.tenant.save()

        response = self.client.get('/')

        self.assertContains(response, 'DASHBOARD')
