# Copyright (c) 2025 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

# pylint: disable=too-many-ancestors
import json

from http import HTTPStatus
from mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings

from django_tenants.utils import tenant_context

from tcms_tenants.tests import TenantGroupsTestCase
from tenant_groups.models import Group as TenantGroup


UserModel = get_user_model()


class TenantInviteApiTestCase(TenantGroupsTestCase):
    @override_settings(DEFAULT_GROUPS=["InvitedUsers"])
    @patch("tcms.core.utils.mailto.send_mail")
    def test_invited_users_are_granted_access(self, send_mail):
        with tenant_context(self.tenant):
            TenantGroup.objects.create(name="InvitedUsers")

        self.assertFalse(
            UserModel.objects.filter(username__startswith="invited-via-rpc").exists()
        )

        valid_addresses = []
        for i in range(90):
            valid_addresses.append(f"invited-via-rpc-{i}@example.com")

        invalid_addresses = []
        for i in range(10):
            invalid_addresses.append(f"invalid-via-rpc-{i}@example.")

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "Tenant.invite",
                "params": [valid_addresses + invalid_addresses, True],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)

        data = json.loads(response.content)["result"]

        self.assertIsInstance(data, dict)
        self.assertIn("success", data)
        self.assertEqual(len(data["success"]), 90)
        self.assertEqual(data["success"], valid_addresses)

        self.assertIn("errored", data)
        self.assertEqual(len(data["errored"]), 10)
        self.assertEqual(data["errored"], invalid_addresses)

        self.assertTrue(send_mail.called)
        self.assertEqual(send_mail.call_count, 90)

        self.assertEqual(
            90, UserModel.objects.filter(username__startswith="invited-via-rpc").count()
        )

        for invited_user in UserModel.objects.filter(
            username__startswith="invited-via-rpc"
        ):
            self.assertTrue(invited_user.is_active)
            self.assertTrue(
                self.tenant.authorized_users.filter(pk=invited_user.pk).exists()
            )

            self.assertTrue(
                invited_user.tenant_groups.filter(name="InvitedUsers").exists()
            )
            self.assertFalse(invited_user.tenant_groups.filter(name="Tester").exists())

        for address in invalid_addresses:
            self.assertFalse(UserModel.objects.filter(email=address).exists())

    @override_settings(DEFAULT_GROUPS=["InvitedUsers"])
    @patch("tcms.core.utils.mailto.send_mail")
    def test_email_not_send_when_explicitly_specified(self, send_mail):
        with tenant_context(self.tenant):
            TenantGroup.objects.create(name="InvitedUsers")

        self.assertFalse(
            UserModel.objects.filter(username__startswith="invited-silently").exists()
        )

        valid_addresses = []
        for i in range(90):
            valid_addresses.append(f"invited-silently-{i}@example.com")

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "Tenant.invite",
                "params": [valid_addresses, False],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)

        data = json.loads(response.content)["result"]

        self.assertIsInstance(data, dict)
        self.assertIn("success", data)
        self.assertEqual(len(data["success"]), 90)
        self.assertEqual(data["success"], valid_addresses)

        self.assertIn("errored", data)
        self.assertEqual(len(data["errored"]), 0)

        self.assertFalse(send_mail.called)

        self.assertEqual(
            90,
            UserModel.objects.filter(username__startswith="invited-silently").count(),
        )
