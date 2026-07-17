# Copyright (c) 2026 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

# pylint: disable=too-many-ancestors, too-many-lines
import json

from http import HTTPStatus

from django.contrib.auth.models import Permission
from django_tenants.utils import tenant_context
from parameterized import parameterized

from tcms.tests import remove_perm_from_user, user_should_have_perm
from tcms_tenants.tests import TenantGroupsTestCase, UserFactory
from tenant_groups.models import Group as TenantGroup


class TenantGroupFilter(TenantGroupsTestCase):
    def test_with_permission(self):
        with tenant_context(self.tenant):
            user_should_have_perm(self.tester, "tenant_groups.view_group")

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TenantGroup.filter",
                "params": [{}],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)

        data = json.loads(response.content)["result"]

        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 2)
        for group in data:
            self.assertIn("id", group)
            self.assertIn("name", group)

    def test_without_permission(self):
        with tenant_context(self.tenant):
            remove_perm_from_user(self.tester, "tenant_groups.view_group")

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TenantGroup.filter",
                "params": [{}],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)

        data = json.loads(response.content)["error"]

        self.assertEqual(
            'Authentication failed when calling "TenantGroup.filter"', data["message"]
        )


class TenantGroupAddPermission(TenantGroupsTestCase):
    def test_with_permission(self):
        with tenant_context(self.tenant):
            user_should_have_perm(self.tester, "tenant_groups.change_group")
            group = TenantGroup.objects.create(name="EmptyGroup")
            self.assertEqual(0, group.permissions.count())

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TenantGroup.add_permission",
                "params": [group.pk, "management.view_product"],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)

        with tenant_context(self.tenant):
            group.refresh_from_db()
            self.assertEqual(1, group.permissions.count())

    def test_without_permission(self):
        with tenant_context(self.tenant):
            remove_perm_from_user(self.tester, "tenant_groups.change_group")

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TenantGroup.add_permission",
                "params": [1, "management.view_product"],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)

        data = json.loads(response.content)["error"]

        self.assertEqual(
            'Authentication failed when calling "TenantGroup.add_permission"',
            data["message"],
        )

    def test_with_missing_group_id(self):
        with tenant_context(self.tenant):
            user_should_have_perm(self.tester, "tenant_groups.change_group")

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TenantGroup.add_permission",
                "params": [99999, "management.view_product"],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)

        data = json.loads(response.content)["error"]

        self.assertIn("Group matching query does not exist", data["message"])

    def test_with_invalid_permission_label(self):
        with tenant_context(self.tenant):
            user_should_have_perm(self.tester, "tenant_groups.change_group")

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TenantGroup.add_permission",
                "params": [1, "management_view_product"],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)

        data = json.loads(response.content)["error"]

        self.assertIn(
            '"management_view_product" should be: app_label.perm_codename',
            data["message"],
        )


class TenantGroupAddUser(TenantGroupsTestCase):
    def test_with_permission(self):
        with tenant_context(self.tenant):
            user_should_have_perm(self.tester, "tenant_groups.change_group")
            group = TenantGroup.objects.create(name="EmptyGroup")
            self.assertEqual(0, group.user_set.count())

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TenantGroup.add_user",
                "params": [group.pk, self.tester.pk],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)

        with tenant_context(self.tenant):
            group.refresh_from_db()
            self.assertEqual(1, group.user_set.count())

    def test_without_permission(self):
        with tenant_context(self.tenant):
            remove_perm_from_user(self.tester, "tenant_groups.change_group")

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TenantGroup.add_user",
                "params": [1, self.tester.pk],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)

        data = json.loads(response.content)["error"]

        self.assertEqual(
            'Authentication failed when calling "TenantGroup.add_user"',
            data["message"],
        )

    def test_with_missing_group_id(self):
        with tenant_context(self.tenant):
            user_should_have_perm(self.tester, "tenant_groups.change_group")

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TenantGroup.add_user",
                "params": [99999, self.tester.pk],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)

        data = json.loads(response.content)["error"]

        self.assertIn("Group matching query does not exist", data["message"])

    def test_with_missing_user_id(self):
        with tenant_context(self.tenant):
            user_should_have_perm(self.tester, "tenant_groups.change_group")
            group = TenantGroup.objects.create(name="EmptyGroup")
            self.assertEqual(0, group.user_set.count())

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TenantGroup.add_user",
                "params": [group.pk, 99999],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)

        data = json.loads(response.content)["error"]

        self.assertIn("User matching query does not exist", data["message"])


class TenantGroupCreate(TenantGroupsTestCase):
    def test_with_permission(self):
        with tenant_context(self.tenant):
            user_should_have_perm(self.tester, "tenant_groups.add_group")
            self.assertFalse(TenantGroup.objects.filter(name="AddedViaApi").exists())

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TenantGroup.create",
                "params": [{"name": "AddedViaApi"}],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)["result"]

        self.assertIsInstance(data, dict)
        self.assertIn("id", data)
        self.assertIn("name", data)
        self.assertEqual(data["name"], "AddedViaApi")

        with tenant_context(self.tenant):
            self.assertTrue(TenantGroup.objects.filter(name="AddedViaApi").exists())

    def test_without_permission(self):
        with tenant_context(self.tenant):
            remove_perm_from_user(self.tester, "tenant_groups.add_group")

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TenantGroup.create",
                "params": [{"name": "AddedWithoutPermission"}],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)

        data = json.loads(response.content)["error"]

        self.assertEqual(
            'Authentication failed when calling "TenantGroup.create"',
            data["message"],
        )

        with tenant_context(self.tenant):
            self.assertFalse(
                TenantGroup.objects.filter(name="AddedWithoutPermission").exists()
            )

    def test_with_invalid_input(self):
        with tenant_context(self.tenant):
            user_should_have_perm(self.tester, "tenant_groups.add_group")

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TenantGroup.create",
                "params": [{}],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)

        data = json.loads(response.content)["error"]

        self.assertEqual(
            "Internal error: [('name', ['This field is required.'])]",
            data["message"],
        )


class MultiTenantAddUser(TenantGroupsTestCase):
    """Multi-tenant tests for TenantGroup.add_user()."""

    @classmethod
    def get_test_schema_name(cls):
        return "tenant_group"

    @classmethod
    def get_test_tenant_domain(cls):
        return "tenant-group.test.com"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create users in public schema
        cls.user_01 = UserFactory()
        cls.user_02 = UserFactory()
        cls.user_03 = UserFactory()
        cls.user_04 = UserFactory()
        cls.user_05 = UserFactory()

        # Setup group and authorized users for the tenant
        with tenant_context(cls.tenant):
            cls.tenant_group = TenantGroup.objects.create(name="TestGroup")
            cls.tenant.authorized_users.add(cls.user_01)
            cls.tenant.authorized_users.add(cls.user_05)

        # Grant tenant_groups permissions so tester can call TenantGroup.add_user
        perms = Permission.objects.filter(
            content_type__app_label__contains="tenant_groups"
        )
        cls.tester.user_permissions.add(*perms)

    def setUp(self):
        super().setUp()

        # Ensure clean state for each test
        with tenant_context(self.tenant):
            self.tenant_group.user_set.clear()

    @parameterized.expand(
        [
            ("user_01", lambda self: self.user_01),
            ("user_05", lambda self: self.user_05),
            ("tester", lambda self: self.tester),
            ("tenant.owner", lambda self: self.tenant.owner),
        ]
    )
    def test_tenantgroup_add_user_api_with_authorized_user_should_work(
        self, _name, get_user
    ):
        user = get_user(self)

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TenantGroup.add_user",
                "params": [self.tenant_group.pk, user.pk],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("result", data)

        with tenant_context(self.tenant):
            self.tenant_group.refresh_from_db()
            self.assertTrue(self.tenant_group.user_set.filter(pk=user.pk).exists())

    @parameterized.expand(
        [
            ("user_02", lambda self: self.user_02),
            ("user_03", lambda self: self.user_03),
            ("user_04", lambda self: self.user_04),
        ]
    )
    def test_tenantgroup_add_user_api_with_unauthorized_user_should_fail(
        self, _name, get_user
    ):
        user = get_user(self)

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TenantGroup.add_user",
                "params": [self.tenant_group.pk, user.pk],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("error", data)
        self.assertIn("User matching query does not exist", data["error"]["message"])

        with tenant_context(self.tenant):
            self.tenant_group.refresh_from_db()
            self.assertFalse(self.tenant_group.user_set.filter(pk=user.pk).exists())
