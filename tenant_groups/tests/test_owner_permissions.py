# Copyright (c) 2022 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

# pylint: disable=invalid-name, too-many-ancestors
from django.urls import reverse

from django_tenants.utils import tenant_context

from tcms.bugs.models import Bug
from tcms.bugs.tests.factory import BugFactory
from tcms.management.models import Priority
from tcms.testcases.models import TestCase, TestCaseStatus
from tcms.tests.factories import (
    BuildFactory,
    CategoryFactory,
    ProductFactory,
    TestCaseFactory,
    VersionFactory,
)

from tcms_tenants.tests import TenantGroupsTestCase


class TestPermissions(TenantGroupsTestCase):
    # Note: self.tenant.owner is already in default groups

    def setUp(self):
        super().setUp()

        self.client.logout()
        self.client.login(username=self.tenant.owner.username, password="password")

    def test_can_view_bug(self):
        with tenant_context(self.tenant):
            existing = BugFactory()

        response = self.client.get(reverse("bugs-get", args=[existing.pk]))
        self.assertContains(response, f"BUG-{existing.pk}")
        self.assertContains(response, existing.summary)

    def test_can_add_bug(self):
        with tenant_context(self.tenant):
            initial_count = Bug.objects.count()

            summary = "A shiny new bug!"
            product = ProductFactory()
            version = VersionFactory(product=product)
            build = BuildFactory(version=version)

        response = self.client.post(
            reverse("bugs-new"),
            {
                "summary": summary,
                "reporter": self.tester.pk,
                "product": product.pk,
                "version": version.pk,
                "build": build.pk,
            },
        )

        with tenant_context(self.tenant):
            bug_created = Bug.objects.last()
            self.assertEqual(Bug.objects.count(), initial_count + 1)

        self.assertRedirects(
            response,
            reverse("bugs-get", args=(bug_created.pk,)),
            status_code=302,
            target_status_code=200,
        )
        self.assertEqual(bug_created.summary, summary)

    def test_can_change_bug(self):
        with tenant_context(self.tenant):
            existing = BugFactory()
            summary_edit = "An edited summary"
            version_edit = VersionFactory(product=existing.product)
            build_edit = BuildFactory(version=version_edit)

        response = self.client.post(
            reverse("bugs-edit", args=(existing.pk,)),
            {
                "summary": summary_edit,
                "version": version_edit.pk,
                "build": build_edit.pk,
                "reporter": existing.reporter.pk,
                "assignee": existing.assignee.pk,
                "product": existing.product.pk,
            },
            follow=True,
        )

        self.assertRedirects(
            response,
            reverse("bugs-get", args=(existing.pk,)),
            status_code=302,
            target_status_code=200,
        )

        with tenant_context(self.tenant):
            existing.refresh_from_db()

        self.assertEqual(existing.summary, summary_edit)
        self.assertEqual(existing.version, version_edit)
        self.assertEqual(existing.build, build_edit)

    def test_can_delete_bug(self):
        with tenant_context(self.tenant):
            existing = BugFactory()
            initial_count = Bug.objects.count()

        response = self.client.post(
            reverse("admin:bugs_bug_delete", args=[existing.pk]),
            {"post": "yes"},
            follow=True,
        )

        self.assertContains(response, "The bug")
        self.assertContains(response, "was deleted successfully")

        with tenant_context(self.tenant):
            self.assertEqual(Bug.objects.count(), initial_count - 1)

    def test_can_view_testcase(self):
        with tenant_context(self.tenant):
            existing = TestCaseFactory()

        response = self.client.get(reverse("testcases-get", args=[existing.pk]))
        self.assertContains(response, f"TC-{existing.pk}")
        self.assertContains(response, existing.summary)

    def test_can_add_testcase(self):
        with tenant_context(self.tenant):
            case = TestCaseFactory()
            case.save()

            initial_count = TestCase.objects.count()

            summary = "summary"
            text = "Given-When-Then"
            script = "some script"
            arguments = "args1, args2, args3"
            requirement = "requirement"
            link = "http://somelink.net"
            notes = "notes"
            category = CategoryFactory()
            data = {
                "author": self.tester.pk,
                "summary": summary,
                "default_tester": self.tester.pk,
                "product": category.product.pk,
                "category": category.pk,
                "case_status": TestCaseStatus.objects.filter(is_confirmed=True)
                .first()
                .pk,
                "priority": Priority.objects.first().pk,
                # specify in human readable format
                "setup_duration": "2 20:10:00",
                "testing_duration": "00:00:00",
                "text": text,
                "script": script,
                "arguments": arguments,
                "requirement": requirement,
                "extra_link": link,
                "notes": notes,
                "email_settings-0-auto_to_case_author": "on",
                "email_settings-0-auto_to_run_manager": "on",
                "email_settings-0-auto_to_execution_assignee": "on",
                "email_settings-0-auto_to_case_tester": "on",
                "email_settings-0-auto_to_run_tester": "on",
                "email_settings-0-notify_on_case_update": "on",
                "email_settings-0-notify_on_case_delete": "on",
                "email_settings-0-cc_list": "info@example.com",
                "email_settings-0-case": "",
                "email_settings-0-id": case.emailing.pk,
                "email_settings-TOTAL_FORMS": "1",
                "email_settings-INITIAL_FORMS": "1",
                "email_settings-MIN_NUM_FORMS": "0",
                "email_settings-MAX_NUM_FORMS": "1",
            }

        response = self.client.post(
            reverse("testcases-new"),
            data,
            follow=True,
        )

        with tenant_context(self.tenant):
            case_created = TestCase.objects.last()
            self.assertEqual(TestCase.objects.count(), initial_count + 1)

        self.assertRedirects(
            response,
            reverse("testcases-get", args=(case_created.pk,)),
            status_code=302,
            target_status_code=200,
        )
        self.assertEqual(case_created.summary, summary)

    def test_can_change_testcase(self):
        with tenant_context(self.tenant):
            existing = TestCaseFactory()

            summary_edit = "An edited summary"
            data = {
                "author": existing.author.pk,
                "summary": summary_edit,
                "default_tester": existing.default_tester.pk,
                "product": existing.category.product.pk,
                "category": existing.category.pk,
                "case_status": existing.case_status.pk,
                "priority": existing.priority.pk,
                # specify in human readable format
                "setup_duration": "2 20:10:00",
                "testing_duration": "00:00:00",
                "text": "Hello There",
                "script": "",
                "arguments": "",
                "requirement": "",
                "extra_link": "",
                "notes": "",
                "email_settings-0-auto_to_case_author": "on",
                "email_settings-0-auto_to_run_manager": "on",
                "email_settings-0-auto_to_execution_assignee": "on",
                "email_settings-0-auto_to_case_tester": "on",
                "email_settings-0-auto_to_run_tester": "on",
                "email_settings-0-notify_on_case_update": "on",
                "email_settings-0-notify_on_case_delete": "on",
                "email_settings-0-cc_list": "info@example.com",
                "email_settings-0-case": "",
                "email_settings-0-id": existing.emailing.pk,
                "email_settings-TOTAL_FORMS": "1",
                "email_settings-INITIAL_FORMS": "1",
                "email_settings-MIN_NUM_FORMS": "0",
                "email_settings-MAX_NUM_FORMS": "1",
            }

        response = self.client.post(
            reverse("testcases-edit", args=(existing.pk,)),
            data,
            follow=True,
        )

        self.assertRedirects(
            response,
            reverse("testcases-get", args=(existing.pk,)),
            status_code=302,
            target_status_code=200,
        )

        with tenant_context(self.tenant):
            existing.refresh_from_db()

        self.assertEqual(existing.summary, summary_edit)

    def test_can_delete_testcase(self):
        with tenant_context(self.tenant):
            existing = TestCaseFactory()
            initial_count = TestCase.objects.count()

        response = self.client.post(
            reverse("admin:testcases_testcase_delete", args=[existing.pk]),
            {"post": "yes"},
            follow=True,
        )

        self.assertContains(response, "The test case")
        self.assertContains(response, "was deleted successfully")

        with tenant_context(self.tenant):
            self.assertEqual(TestCase.objects.count(), initial_count - 1)
