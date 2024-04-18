# Copyright (c) 2019-2022 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt
# pylint: disable=too-many-ancestors
from datetime import timedelta

from django.conf import settings
from django.test import modify_settings
from django.test import TestCase
from django.test.client import RequestFactory
from django.utils import timezone
from django.http import HttpResponseForbidden, HttpResponseNotFound

from tcms_tenants.tests import LoggedInTestCase
from tcms_tenants.context_processors import tenant_navbar_processor


class ContextProcessor(TestCase):
    def test_without_tenant(self):
        """
        This simulates the case where TenantMainMiddleware returns a 404 for
        non-existing tenant but there's no request.tenant attribute and the
        follow-up post-processing fails with a 500.
        """
        factory = RequestFactory()
        request = factory.get("/robots.txt", HTTP_HOST="non-existing.tenant.bg")

        result = tenant_navbar_processor(request)
        self.assertEqual(result, {"CUSTOMIZED_LOGO_CONTENTS": ""})


class BlockUnauthorizedUserMiddlewareTestCase(LoggedInTestCase):
    def test_unauthorized_user_cant_access_tenant(self):
        self.assertFalse(self.tenant.publicly_readable)

        self.tenant.authorized_users.remove(self.tester)
        response = self.client.get("/")

        self.assertIsInstance(response, HttpResponseForbidden)
        self.assertIn(
            "Unauthorized", str(response.content, encoding=settings.DEFAULT_CHARSET)
        )


class BlockUnpaidTenantMiddlewareTestCase(LoggedInTestCase):

    @modify_settings(
        MIDDLEWARE={
            "append": "tcms_tenants.middleware.BlockUnpaidTenantMiddleware",
        }
    )
    def test_paid_until_is_none_access_forbidden(self):
        self.tenant.paid_until = None
        self.tenant.save()

        response = self.client.get("/")

        self.assertIsInstance(response, HttpResponseForbidden)
        self.assertIn(
            "Unpaid", str(response.content, encoding=settings.DEFAULT_CHARSET)
        )

    @modify_settings(
        MIDDLEWARE={
            "append": "tcms_tenants.middleware.BlockUnpaidTenantMiddleware",
        }
    )
    def test_paid_until_lt_today_access_forbidden(self):
        self.tenant.paid_until = timezone.now() - timedelta(days=1)
        self.tenant.save()

        response = self.client.get("/")

        self.assertIsInstance(response, HttpResponseForbidden)
        self.assertIn(
            "Unpaid", str(response.content, encoding=settings.DEFAULT_CHARSET)
        )

    @modify_settings(
        MIDDLEWARE={
            "append": "tcms_tenants.middleware.BlockUnpaidTenantMiddleware",
        }
    )
    def test_paid_until_expires_within_week_warning_shown(self):
        self.tenant.paid_until = timezone.now() + timedelta(days=3)
        self.tenant.save()

        response = self.client.get("/")

        self.assertContains(response, "Tenant expires in less than 7 days")

    @modify_settings(
        MIDDLEWARE={
            "append": "tcms_tenants.middleware.BlockUnpaidTenantMiddleware",
        }
    )
    def test_paid_until_gt_today_access_granted(self):
        self.tenant.paid_until = timezone.now() + timedelta(days=30)
        self.tenant.save()

        response = self.client.get("/")

        self.assertContains(response, "DASHBOARD")


class InvalidHostname(LoggedInTestCase):
    @classmethod
    def get_test_tenant_domain(cls):
        # This domain is not valid according to RFC 1034/1035
        return "_.kiwitcms.eu"

    @classmethod
    def get_test_schema_name(cls):
        # we need a different schema name here so that it gets created
        return "_underscore"

    def test_invalid_hostname_should_return_404(self):
        response = self.client.get("/")

        self.assertIsInstance(response, HttpResponseNotFound)
