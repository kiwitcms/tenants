# Copyright (c) 2026 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

# pylint: disable=too-many-ancestors

from io import StringIO

from django.core.management import call_command

from django_tenants.utils import tenant_context
from simple_history.utils import get_history_model_for_model

from tcms.testcases.models import TestCase
from tcms.tests.factories import TestCaseFactory

from tcms_tenants.tests import TenantGroupsTestCase, tenants_with_schema


class PopulateTenantHistoryTestCase(TenantGroupsTestCase):
    model = "testcases.TestCase"
    instances_per_tenant = 3

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        for tenant in tenants_with_schema():
            with tenant_context(tenant):
                for _ in range(cls.instances_per_tenant):
                    test_case = TestCaseFactory()
                    test_case.save()  # creates a history record
                    test_case.emailing.notify_on_case_update = False
                    test_case.emailing.save()

                # emulate objects which existed before history was enabled
                get_history_model_for_model(TestCase).objects.all().delete()

    def test_populates_history_for_all_tenants(self):
        tenants = tenants_with_schema()
        self.assertGreaterEqual(len(tenants), 1)

        history_model = get_history_model_for_model(TestCase)
        for tenant in tenants:
            with tenant_context(tenant):
                self.assertTrue(TestCase.objects.exists())
                self.assertFalse(history_model.objects.exists())

        out = StringIO()
        call_command(
            "populate_tenant_history",
            self.model,
            verbosity=1,
            stdout=out,
        )

        output = out.getvalue()

        for tenant in tenants:
            with tenant_context(tenant):
                self.assertEqual(
                    history_model.objects.count(), TestCase.objects.count()
                )

            for banner in ("Populating history", "End populating history"):
                self.assertIn(
                    f"=== {banner} for tenant '{tenant.schema_name}' ===",
                    output,
                )

    def test_dry_run_does_not_populate_history(self):
        tenants = tenants_with_schema()
        self.assertGreaterEqual(len(tenants), 1)

        history_model = get_history_model_for_model(TestCase)

        out = StringIO()
        call_command(
            "populate_tenant_history",
            self.model,
            dry_run=True,
            verbosity=1,
            stdout=out,
        )

        output = out.getvalue()

        for tenant in tenants:
            with tenant_context(tenant):
                self.assertFalse(history_model.objects.exists())

            self.assertIn(
                f"for tenant '{tenant.schema_name}' === dry run: True ===",
                output,
            )
