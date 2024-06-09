# Copyright (c) 2021-2022 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

# pylint: disable=too-many-ancestors

from django.contrib.auth.models import Group, Permission
from django.urls import reverse
from django.http import HttpResponseForbidden

from tcms_tenants.tests import LoggedInTestCase, UserFactory
from tenant_groups.models import Group as TenantGroup


class PubliclyReadableTenantTestCase(LoggedInTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # the tenant is publicly readable
        cls.tenant.publicly_readable = True
        cls.tenant.save()

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

        # tenant perms
        tenant_tester, _created = TenantGroup.objects.get_or_create(name="Tester")
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
            tenant_tester.permissions.add(*app_perms)

        # self.tester is not authorized
        # and isn't assigned to any tenant groups b/c that's not possible
        cls.tenant.authorized_users.remove(cls.tester)
        # public group permissions don't apply here
        tester.user_set.add(cls.tester)

        # regular_user doesn't have any permissions assigned
        # via tenant-groups
        cls.regular_user = UserFactory()
        cls.regular_user.set_password("password")
        cls.regular_user.save()
        # but is authorized so they should only be able to view
        cls.tenant.authorized_users.add(cls.regular_user)
        # public group permissions don't apply here
        tester.user_set.add(cls.regular_user)

    @classmethod
    def tearDownClass(cls):
        cls.tenant.publicly_readable = False
        cls.tenant.save()

    def test_unauthorized_user_can_view(self):
        response = self.client.get(
            reverse("test_plan_url_short", args=[self.test_plan_by_owner.pk]),
            follow=True,
        )

        self.assertContains(response, self.test_plan_by_owner.name)
        self.assertContains(response, f"TP-{self.test_plan_by_owner.pk}")
        self.assertContains(response, self.test_plan_by_owner.text)

    def test_unauthorized_user_cannot_add(self):
        target_url = reverse("plans-new")
        response = self.client.get(target_url)
        self.assertRedirects(response, reverse("tcms-login") + "?next=" + target_url)

    def test_unauthorized_user_cannot_edit(self):
        target_url = reverse("plan-edit", args=[self.test_plan_by_owner.pk])
        response = self.client.get(target_url)
        self.assertRedirects(response, reverse("tcms-login") + "?next=" + target_url)

    def test_unauthorized_user_cannot_delete(self):
        response = self.client.get(
            reverse(
                "admin:testplans_testplan_delete", args=[self.test_plan_by_owner.pk]
            ),
        )
        self.assertIsInstance(response, HttpResponseForbidden)

    def test_anonymous_user_can_view(self):
        self.client.logout()

        response = self.client.get(
            reverse("test_plan_url_short", args=[self.test_plan_by_owner.pk]),
            follow=True,
        )

        self.assertContains(response, self.test_plan_by_owner.name)
        self.assertContains(response, f"TP-{self.test_plan_by_owner.pk}")
        self.assertContains(response, self.test_plan_by_owner.text)

    def test_anonymous_user_cannot_add(self):
        self.client.logout()

        target_url = reverse("plans-new")
        response = self.client.get(target_url)
        self.assertRedirects(response, reverse("tcms-login") + "?next=" + target_url)

    def test_anonymous_user_cannot_edit(self):
        self.client.logout()

        target_url = reverse("plan-edit", args=[self.test_plan_by_owner.pk])
        response = self.client.get(target_url)
        self.assertRedirects(response, reverse("tcms-login") + "?next=" + target_url)

    def test_anonymous_user_cannot_delete(self):
        self.client.logout()

        target_url = reverse(
            "admin:testplans_testplan_delete", args=[self.test_plan_by_owner.pk]
        )
        response = self.client.get(target_url)
        self.assertRedirects(response, "/admin/login/?next=" + target_url)

    def test_authorized_user_without_group_permissions_can_view(self):
        self.client.logout()
        self.client.login(username=self.regular_user.username, password="password")

        response = self.client.get(
            reverse("test_plan_url_short", args=[self.test_plan_by_owner.pk]),
            follow=True,
        )

        self.assertContains(response, self.test_plan_by_owner.name)
        self.assertContains(response, f"TP-{self.test_plan_by_owner.pk}")
        self.assertContains(response, self.test_plan_by_owner.text)

    def test_authorized_user_without_group_permissions_cannot_add(self):
        self.client.logout()
        self.client.login(username=self.regular_user.username, password="password")

        target_url = reverse("plans-new")
        response = self.client.get(target_url)
        self.assertRedirects(response, reverse("tcms-login") + "?next=" + target_url)

    def test_authorized_user_without_group_permissions_cannot_edit(self):
        self.client.logout()
        self.client.login(username=self.regular_user.username, password="password")

        target_url = reverse("plan-edit", args=[self.test_plan_by_owner.pk])
        response = self.client.get(target_url)
        self.assertRedirects(response, reverse("tcms-login") + "?next=" + target_url)

    def test_authorized_user_without_group_permissions_cannot_delete(self):
        self.client.logout()
        self.client.login(username=self.regular_user.username, password="password")

        response = self.client.get(
            reverse(
                "admin:testplans_testplan_delete", args=[self.test_plan_by_owner.pk]
            ),
        )
        self.assertIsInstance(response, HttpResponseForbidden)
