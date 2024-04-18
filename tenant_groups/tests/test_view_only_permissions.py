# pylint: disable=invalid-name, too-many-ancestors
from django.contrib.auth.models import Group, Permission
from django.http import HttpResponseForbidden
from django.urls import reverse

from django_tenants.utils import tenant_context

from tcms.bugs.tests.factory import BugFactory
from tcms.tests.factories import TestCaseFactory

from tcms_tenants.tests import TenantGroupsTestCase, UserFactory
from tenant_groups.models import Group as TenantGroup


class TestPermissions(TenantGroupsTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.regular_user = UserFactory()
        cls.regular_user.is_superuser = False
        cls.regular_user.set_password("password")
        cls.regular_user.save()

        with tenant_context(cls.tenant):
            # tenant perms
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
            view_only.user_set.add(cls.regular_user)

            # authorize this user
            cls.tenant.authorized_users.add(cls.regular_user)

        # give all perms for the public tenant group
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
            )
            tester.permissions.add(*app_perms)

        # add user to the Tester group on public tenant
        # that should not affect permission behavior on the tenant
        tester.user_set.add(cls.regular_user)

    def setUp(self):
        super().setUp()

        with tenant_context(self.tenant):
            # make sure user isn't part of any other tenant groups
            self.assertEqual(1, self.regular_user.tenant_groups.count())

        # perform all operations not as the tenant owner
        self.client.logout()
        self.client.login(username=self.regular_user.username, password="password")

    def test_can_view_bug(self):
        with tenant_context(self.tenant):
            existing = BugFactory()

        response = self.client.get(reverse("bugs-get", args=[existing.pk]))
        self.assertContains(response, f"BUG-{existing.pk}")
        self.assertContains(response, existing.summary)

    def test_cannot_add_bug(self):
        url = reverse("bugs-new")
        response = self.client.get(url, follow=True)
        self.assertRedirects(response, f"/accounts/login/?next={url}")

    def test_cannot_change_bug(self):
        with tenant_context(self.tenant):
            existing = BugFactory()

        url = reverse("bugs-edit", args=(existing.pk,))
        response = self.client.get(url, follow=True)
        self.assertRedirects(response, f"/accounts/login/?next={url}")

    def test_cannot_delete_bug(self):
        with tenant_context(self.tenant):
            existing = BugFactory()

        url = reverse("admin:bugs_bug_delete", args=[existing.pk])
        response = self.client.post(
            url,
            {"post": "yes"},
            follow=True,
        )
        self.assertIsInstance(response, HttpResponseForbidden)

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
