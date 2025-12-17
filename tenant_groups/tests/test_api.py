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
