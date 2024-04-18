# pylint: disable=invalid-name, too-many-ancestors
from http import HTTPStatus

from django.contrib.auth.models import Permission
from django.urls import reverse
from django.utils.text import capfirst
from django.utils.translation import gettext_lazy as _

from django_tenants.utils import tenant_context
from tcms_tenants.tests import TenantGroupsTestCase, UserFactory
from tenant_groups.models import Group as TenantGroup


class TestGroupAdmin(TenantGroupsTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.non_authorized_user = UserFactory()

        cls.random_user = UserFactory()
        cls.random_user.set_password("password")
        cls.random_user.save()

        # assign perms for cls.tester b/c they're not in any of the default groups
        perms = Permission.objects.filter(
            content_type__app_label__contains="tenant_groups"
        )
        cls.tester.user_permissions.add(*perms)

        with tenant_context(cls.tenant):
            # authorize random_user
            cls.tenant.authorized_users.add(cls.random_user)

            cls.group = TenantGroup.objects.create(name="New Tenant Group")
            cls.defaultGroups = TenantGroup.objects.filter(
                name__in=["Administrator", "Tester"]
            )

    def tearDown(self):
        super().tearDown()
        self.client.logout()

    def test_user_with_perms_should_not_be_allowed_to_change_default_groups(self):
        for group in self.defaultGroups:
            response = self.client.get(
                reverse("admin:tenant_groups_group_change", args=[group.id])
            )
            self.assertNotContains(
                response,
                f'<input type="text" name="name" value="{group.name}" class="vTextField"'
                ' maxlength="150" required="" id="id_name">',
            )
            self.assertContains(
                response, f'<div class="grp-readonly">{group.name}</div>'
            )

    def test_user_with_perms_should_not_be_allowed_to_delete_default_groups(self):
        for group in self.defaultGroups:
            response = self.client.get(
                reverse("admin:tenant_groups_group_change", args=[group.id])
            )
            _expected_url = reverse("admin:tenant_groups_group_delete", args=[group.id])
            _delete = _("Delete")
            self.assertNotContains(
                response,
                f'<a href="{_expected_url}" class="grp-button grp-delete-link">{_delete}</a>',
            )

    def test_user_with_perms_should_be_allowed_to_create_new_group(self):
        response = self.client.get(reverse("admin:tenant_groups_group_add"))
        _add_group = _("Add %s") % _("group")
        self.assertContains(response, f"<h1>{_add_group}</h1>")
        self.assertContains(
            response,
            '<input type="text" name="name" class="vTextField" '
            'maxlength="150" required id="id_name">',
        )

        # check for the user widget
        self.assertContains(
            response,
            '<select name="users" id="id_users" multiple '
            'class="selectfilter" data-field-name="users" data-is-stacked="0">',
        )
        _capfirst = capfirst(_("users"))
        self.assertContains(response, f'<label for="id_users">{_capfirst}')

    def test_user_with_perms_should_be_able_to_delete_a_non_default_group(self):
        response = self.client.get(
            reverse("admin:tenant_groups_group_delete", args=[self.group.id]),
            follow=True,
        )
        _are_you_sure = _("Are you sure?")
        self.assertContains(response, f"<h1>{_are_you_sure}</h1>")

    def test_user_with_perms_should_be_able_to_edit_a_non_default_group(self):
        response = self.client.get(
            reverse("admin:tenant_groups_group_change", args=[self.group.id])
        )
        self.assertContains(
            response,
            f'<input type="text" name="name" value="{self.group.name}" class="vTextField"'
            ' maxlength="150" required id="id_name">',
        )

    def test_new_group_shows_only_authorized_users(self):
        response = self.client.get(reverse("admin:tenant_groups_group_add"))

        for user in (self.tenant.owner, self.tester, self.random_user):
            self.assertContains(
                response,
                f'<option value="{user.pk}">{user.username}</option>',
            )

        self.assertNotContains(
            response,
            f'<option value="{self.non_authorized_user.pk}">'
            f"{self.non_authorized_user.username}</option>",
        )

    def test_change_group_shows_only_authorized_users(self):
        response = self.client.get(
            reverse("admin:tenant_groups_group_change", args=[self.group.id])
        )

        for user in (self.tenant.owner, self.tester, self.random_user):
            self.assertContains(
                response,
                f'<option value="{user.pk}">{user.username}</option>',
            )

        self.assertNotContains(
            response,
            f'<option value="{self.non_authorized_user.pk}">'
            f"{self.non_authorized_user.username}</option>",
        )

    def test_new_group_shows_only_filtered_permissions(self):
        response = self.client.get(reverse("admin:tenant_groups_group_add"))

        for permission in (
            "Attachments | attachment | Can change attachment",
            "Bugs | bug | Can add bug",
            "Django_Comments | comment | Can delete comment",
            "Linkreference | link reference | Can view link reference",
            "Management | product | Can view product",
            "Testcases | category | Can add category",
            "Testplans | test plan | Can delete test plan",
            "Testruns | test execution | Can delete test execution",
        ):
            self.assertContains(response, permission)

        for permission in (
            "admin |",
            "auth |",
            "captcha |",
            "contenttypes |",
            "kiwi_auth |",
            "sessions |",
            "sites |",
            "social_django |",
            "tcms_tenants |",
        ):
            self.assertNotContains(response, permission)

    def test_change_group_shows_only_filtered_permissions(self):
        for group in self.defaultGroups:
            response = self.client.get(
                reverse("admin:tenant_groups_group_change", args=[group.id])
            )

            for permission in (
                "Attachments | attachment | Can change attachment",
                "Bugs | bug | Can add bug",
                "Django_Comments | comment | Can delete comment",
                "Linkreference | link reference | Can view link reference",
                "Management | product | Can view product",
                "Testcases | category | Can add category",
                "Testplans | test plan | Can delete test plan",
                "Testruns | test execution | Can delete test execution",
            ):
                self.assertContains(response, permission)

            for permission in (
                "admin |",
                "auth |",
                "captcha |",
                "contenttypes |",
                "kiwi_auth |",
                "sessions |",
                "sites |",
                "social_django |",
                "tcms_tenants |",
            ):
                self.assertNotContains(response, permission)

    def test_user_with_perms_should_be_allowed_to_create_new_group_with_added_user(
        self,
    ):
        group_name = "TenantGroupName"
        self.assertFalse(
            self.random_user.tenant_groups.filter(name=group_name).exists()
        )

        response = self.client.post(
            reverse("admin:tenant_groups_group_add"),
            {"name": group_name, "users": [self.random_user.id]},
            follow=True,
        )

        group = TenantGroup.objects.get(name=group_name)

        self.assertIsNotNone(group)
        self.assertContains(response, group_name)
        group_url = reverse("admin:tenant_groups_group_change", args=[group.pk])
        self.assertContains(
            response,
            f'<a href="{group_url}">{group_name}</a>',
        )
        self.assertTrue(self.random_user.tenant_groups.filter(name=group.name).exists())

    def test_user_with_perms_should_be_able_to_add_user_while_editing_a_group(self):
        self.assertFalse(
            self.random_user.tenant_groups.filter(name=self.group.name).exists()
        )
        response = self.client.post(
            reverse("admin:tenant_groups_group_change", args=[self.group.id]),
            {
                "name": self.group.name,
                "users": [self.random_user.id],
                "_continue": True,
            },
            follow=True,
        )

        self.assertContains(
            response,
            f'<option value="{self.random_user.pk}" selected>{self.random_user.username}</option>',
        )
        self.assertTrue(
            self.random_user.tenant_groups.filter(name=self.group.name).exists()
        )

    def test_user_without_perms_should_not_be_able_to_delete_groups(self):
        self.client.logout()
        self.client.login(username=self.random_user.username, password="password")

        response = self.client.get(
            reverse("admin:tenant_groups_group_delete", args=[self.group.id]),
            follow=True,
        )
        self.assertEqual(HTTPStatus.FORBIDDEN, response.status_code)

    def test_user_without_perms_should_not_be_able_to_edit_groups(self):
        self.client.logout()
        self.client.login(username=self.random_user.username, password="password")

        response = self.client.get(
            reverse("admin:tenant_groups_group_change", args=[self.group.id])
        )
        self.assertEqual(HTTPStatus.FORBIDDEN, response.status_code)

    def test_user_without_perms_should_not_be_able_to_create_new_group(self):
        self.client.logout()
        self.client.login(username=self.random_user.username, password="password")

        group_name = "TenantGroupName"
        response = self.client.post(
            reverse("admin:tenant_groups_group_add"),
            {"name": group_name},
            follow=True,
        )
        self.assertEqual(HTTPStatus.FORBIDDEN, response.status_code)
