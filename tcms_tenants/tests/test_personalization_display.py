# Copyright (c) 2022-2024 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

# pylint: disable=too-many-ancestors

from django.urls import reverse
from django_tenants.utils import schema_context

from tcms_tenants.tests import LoggedInTestCase


class WhenOrganizationValueIsSet(LoggedInTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        with schema_context("public"):
            cls.tenant.organization = "Demo Instance"
            cls.tenant.name = "demonstration"
            cls.tenant.save()

    def test_display(self):
        response = self.client.get(reverse("tcms-login"))

        self.assertContains(response, "<span>Demo Instance</span>")
        self.assertNotContains(response, "demonstration")
        self.assertNotContains(response, self.tenant.schema_name)


class WhenNameValueIsSetAndOrganizationValueIsNotSet(LoggedInTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        with schema_context("public"):
            cls.tenant.organization = ""
            cls.tenant.name = "demonstration"
            cls.tenant.save()

    def test_display(self):
        response = self.client.get(reverse("tcms-login"))

        self.assertNotContains(response, "Demo Instance")
        self.assertContains(response, "<span>demonstration</span>")
        self.assertNotContains(response, self.tenant.schema_name)


class WhenNameAndOrganizationValuesAreNotSet(LoggedInTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        with schema_context("public"):
            cls.tenant.organization = ""
            cls.tenant.name = ""
            cls.tenant.save()

    def test_display(self):
        response = self.client.get(reverse("tcms-login"))

        self.assertNotContains(response, "Demo Instance")
        self.assertNotContains(response, "demonstration")
        self.assertContains(response, self.tenant.schema_name)
