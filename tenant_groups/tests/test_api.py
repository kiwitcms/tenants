# Copyright (c) 2025 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

# pylint: disable=too-many-ancestors
import json

from http import HTTPStatus

from django_tenants.utils import tenant_context

from tcms.tests import remove_perm_from_user, user_should_have_perm
from tcms_tenants.tests import TenantGroupsTestCase
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
