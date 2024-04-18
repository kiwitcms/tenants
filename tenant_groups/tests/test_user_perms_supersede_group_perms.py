# pylint: disable=invalid-name, too-many-ancestors
from django.contrib.auth.models import Group, Permission
from django.http import HttpResponseForbidden
from django.urls import reverse

from django_tenants.utils import tenant_context

from tcms.bugs.models import Bug
from tcms.bugs.tests.factory import BugFactory
from tcms.tests.factories import (
    BuildFactory,
    ProductFactory,
    TestCaseFactory,
    VersionFactory,
)

from tcms_tenants.tests import TenantGroupsTestCase, UserFactory
from tenant_groups.models import Group as TenantGroup


class TestPermissions(TenantGroupsTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # power_user has *all* Bug permissions assigned directly
        cls.power_user = UserFactory()
        cls.power_user.set_password("password")
        cls.power_user.save()

        bug_perms = Permission.objects.filter(content_type__app_label__contains="bugs")
        cls.power_user.user_permissions.add(*bug_perms)

        with tenant_context(cls.tenant):
            # and *view* permissions assigned via tenant-groups
            view_only, _created = TenantGroup.objects.get_or_create(name="Viewer")
            for app_name in [
                "bugs",
                "django_comments",
                "linkreference",
                "management",
                "testcases",
                "testplans",
                "testruns",
                "attachments",
            ]:
                app_perms = Permission.objects.filter(
                    content_type__app_label__contains=app_name,
                    codename__startswith="view_",
                )
                view_only.permissions.add(*app_perms)

            # add user to the group
            view_only.user_set.add(cls.power_user)

            # authorize users
            cls.tenant.authorized_users.add(cls.power_user)

        # give all perms except *delete* to the public tenant group
        tester, _created = Group.objects.get_or_create(name="Tester")
        for app_name in [
            "bugs",
            "django_comments",
            "linkreference",
            "management",
            "testcases",
            "testplans",
            "testruns",
            "attachments",
        ]:
            app_perms = Permission.objects.filter(
                content_type__app_label__contains=app_name,
            ).exclude(codename__startswith="delete_")
            tester.permissions.add(*app_perms)

        # add users to the Tester group on public tenant
        # that should not affect permission behavior on the tenant
        tester.user_set.add(cls.power_user)

    def setUp(self):
        super().setUp()

        with tenant_context(self.tenant):
            # make sure user isn't part of any other tenant groups
            self.assertEqual(1, self.power_user.tenant_groups.count())

        # perform all operations as power_user
        self.client.logout()
        self.client.login(username=self.power_user.username, password="password")

    def test_can_view_bug(self):
        with tenant_context(self.tenant):
            existing = BugFactory()

        response = self.client.get(reverse("bugs-get", args=[existing.pk]))
        self.assertContains(response, f"BUG-{existing.pk}")
        self.assertContains(response, existing.summary)

    def test_can_add_bug(self):
        summary = "A shiny new bug!"

        with tenant_context(self.tenant):
            initial_count = Bug.objects.count()
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

        self.assertRedirects(
            response,
            reverse("bugs-get", args=(bug_created.pk,)),
            status_code=302,
            target_status_code=200,
        )

        with tenant_context(self.tenant):
            self.assertEqual(Bug.objects.count(), initial_count + 1)
            self.assertEqual(bug_created.summary, summary)

    def test_can_change_bug(self):
        summary_edit = "An edited summary"

        with tenant_context(self.tenant):
            existing = BugFactory()
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

    def test_cannot_add_testcase(self):
        url = reverse("testcases-new")
        response = self.client.get(url, follow=True)
        self.assertRedirects(response, f"/accounts/login/?next={url}")

    def test_cannot_change_testcase(self):
        with tenant_context(self.tenant):
            existing = TestCaseFactory()

        url = reverse("testcases-edit", args=(existing.pk,))
        response = self.client.get(url, follow=True)
        self.assertRedirects(response, f"/accounts/login/?next={url}")

    def test_cannot_delete_testcase(self):
        with tenant_context(self.tenant):
            existing = TestCaseFactory()

        url = reverse("admin:testcases_testcase_delete", args=[existing.pk])
        response = self.client.post(
            url,
            {"post": "yes"},
            follow=True,
        )
        self.assertIsInstance(response, HttpResponseForbidden)
