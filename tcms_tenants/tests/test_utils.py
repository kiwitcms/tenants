# Copyright (c) 2021-2024 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt
# pylint: disable=too-many-ancestors

from django.test import override_settings
from django_tenants import utils as django_tenant_utils

from tcms.tests import deny_certain_email_addresses

from tcms_tenants import utils
from tcms_tenants.tests import LoggedInTestCase


class TenantDomainTestCase(LoggedInTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        with utils.schema_context("public"):
            cls.tenant2 = django_tenant_utils.get_tenant_model()(
                schema_name="other2", owner=cls.tester
            )
            cls.tenant2.save()

            cls.domain2 = django_tenant_utils.get_tenant_domain_model()(
                tenant=cls.tenant2, domain="other2.example.com"
            )
            cls.domain2.save()

    def test_should_return_existing_domain_from_db(self):
        with override_settings(KIWI_TENANTS_DOMAIN="qa.kiwitcms.org"):
            result = utils.tenant_domain(self.tenant2.schema_name)
            self.assertEqual(result, "other2.example.com")

    def test_should_fallback_to_prefix_and_settings_when_domain_doesnt_exist(self):
        with override_settings(KIWI_TENANTS_DOMAIN="qa.kiwitcms.org"):
            result = utils.tenant_domain("public")
            self.assertEqual(result, "public.qa.kiwitcms.org")


class CreateUserAccountTestCase(LoggedInTestCase):
    def test_should_throw_validation_error_when_used_with_blacklisted_email_address(
        self,
    ):
        with override_settings(
            EMAIL_VALIDATORS=(deny_certain_email_addresses,),
        ):
            with self.assertRaisesRegex(
                ValueError,
                "The User could not be created because the data didn't validate",
            ):
                utils.create_user_account("invalid@yahoo.com")
