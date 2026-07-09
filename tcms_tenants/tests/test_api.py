# Copyright (c) 2025-2026 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

# pylint: disable=too-many-ancestors
import json

from http import HTTPStatus
from mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone

from django_tenants import utils
from parameterized import parameterized
from tcms.tests.factories import ProductFactory

from tcms_tenants.tests import TenantGroupsTestCase, UserFactory
from tenant_groups.models import Group as TenantGroup

UserModel = get_user_model()


class TenantInviteApiTestCase(TenantGroupsTestCase):
    @override_settings(DEFAULT_GROUPS=["InvitedUsers"])
    @patch("tcms.core.utils.mailto.send_mail")
    def test_invited_users_are_granted_access(self, send_mail):
        with utils.tenant_context(self.tenant):
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
        with utils.tenant_context(self.tenant):
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


class ComponentCreateApiTestCase(TenantGroupsTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create users user_01..user_05 in public schema
        cls.user_01 = UserFactory()
        cls.user_02 = UserFactory()
        # user_03 is not authorized for either tenant
        cls.user_03 = UserFactory()
        cls.user_04 = UserFactory()
        cls.user_05 = UserFactory()

        # Setup self.tester and users 01, 05 for self.tenant
        with utils.tenant_context(cls.tenant):
            TenantGroup.objects.get(name="Tester").user_set.add(cls.tester)
            cls.tenant.authorized_users.add(cls.user_01)
            cls.tenant.authorized_users.add(cls.user_05)

        # Create second tenant
        with utils.schema_context("public"):
            ts = int(timezone.now().timestamp())
            cls.tenant2 = utils.get_tenant_model()(
                schema_name=f"tenant_{ts}",
                owner=cls.user_02,
            )
            cls.tenant2.save()

            cls.domain2 = utils.get_tenant_domain_model()(
                tenant=cls.tenant2, domain=f"second-{ts}.example.com"
            )
            cls.domain2.save()

        # User 02 is the owner of tenant2, user 04 is also authorized
        with utils.tenant_context(cls.tenant2):
            cls.tenant2.authorized_users.add(cls.user_02)
            cls.tenant2.authorized_users.add(cls.user_04)

        cls.product = ProductFactory()

    @parameterized.expand(
        [
            ("user_01", lambda self: self.user_01),
            ("user_05", lambda self: self.user_05),
            ("tester", lambda self: self.tester),
            ("tenant.owner", lambda self: self.tenant.owner),
        ]
    )
    def test_component_create_with_authorized_user(self, _, get_user):
        initial_owner = get_user(self)

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "Component.create",
                "params": [
                    {
                        "name": f"Component for {initial_owner.username}",
                        "product": self.product.pk,
                        "initial_owner": initial_owner.pk,
                    }
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("result", data)
        component = data["result"]
        self.assertEqual(component["name"], f"Component for {initial_owner.username}")
        self.assertEqual(component["initial_owner"], initial_owner.pk)

    @parameterized.expand(
        [
            ("user_02", lambda self: self.user_02),
            ("user_03", lambda self: self.user_03),
            ("user_04", lambda self: self.user_04),
        ]
    )
    def test_component_create_with_unauthorized_user(self, _, get_user):
        initial_owner = get_user(self)

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "Component.create",
                "params": [
                    {
                        "name": f"Component for {initial_owner.username}",
                        "product": self.product.pk,
                        "initial_owner": initial_owner.pk,
                    }
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("error", data)
        self.assertRegex(
            data["error"]["message"], r"initial_owner.*Select a valid choice"
        )
