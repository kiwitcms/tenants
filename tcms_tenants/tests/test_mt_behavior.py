# Copyright (c) 2026 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

# pylint: disable=too-many-ancestors
import json

from http import HTTPStatus

from django.urls import reverse
from django.utils import timezone

from django_tenants import utils
from parameterized import parameterized
from tcms.bugs.models import Bug
from tcms.bugs.tests.factory import BugFactory
from tcms.tests.factories import (
    BuildFactory,
    ComponentFactory,
    ProductFactory,
    VersionFactory,
)

from tcms_tenants.tests import TenantGroupsTestCase, UserFactory
from tenant_groups.models import Group as TenantGroup


class MultiTenantBehavior(TenantGroupsTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "multi"

    @classmethod
    def get_test_tenant_domain(cls):
        return "multi.test.com"

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
            cls.product = ProductFactory()
            cls.component = ComponentFactory(product=cls.product)
            cls.version = VersionFactory(product=cls.product)
            cls.build = BuildFactory(version=cls.version)
            cls.bug = BugFactory(
                reporter=cls.tester,
                assignee=cls.tester,
                product=cls.product,
                version=cls.version,
                build=cls.build,
            )
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

    def test_component_admin_add_dropdown_contains_only_authorized_users(self):
        response = self.client.get(reverse("admin:management_component_add"))

        self.assertContains(response, self.user_01.username)
        self.assertContains(response, self.user_05.username)
        self.assertContains(response, self.tester.username)
        self.assertContains(response, self.tenant.owner.username)

        self.assertNotContains(response, self.user_02.username)
        self.assertNotContains(response, self.user_03.username)
        self.assertNotContains(response, self.user_04.username)

    @parameterized.expand(
        [
            ("user_01", lambda self: self.user_01),
            ("user_05", lambda self: self.user_05),
            ("tester", lambda self: self.tester),
            ("tenant.owner", lambda self: self.tenant.owner),
        ]
    )
    def test_component_create_api_with_authorized_user_should_work(self, _, get_user):
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
    def test_component_create_api_with_unauthorized_user_should_fail(self, _, get_user):
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

    @parameterized.expand(
        [
            ("user_01", lambda self: self.user_01),
            ("user_05", lambda self: self.user_05),
            ("tester", lambda self: self.tester),
            ("tenant.owner", lambda self: self.tenant.owner),
        ]
    )
    def test_component_update_api_with_authorized_user_should_work(self, _, get_user):
        new_owner = get_user(self)

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "Component.update",
                "params": [
                    self.component.pk,
                    {
                        "initial_owner": new_owner.pk,
                    },
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("result", data)
        self.assertEqual(data["result"]["initial_owner"], new_owner.pk)

    @parameterized.expand(
        [
            ("user_02", lambda self: self.user_02),
            ("user_03", lambda self: self.user_03),
            ("user_04", lambda self: self.user_04),
        ]
    )
    def test_component_update_api_with_unauthorized_user_should_fail(self, _, get_user):
        new_owner = get_user(self)

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "Component.update",
                "params": [
                    self.component.pk,
                    {
                        "initial_owner": new_owner.pk,
                    },
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

    #
    # bugs-new URL
    #
    @parameterized.expand(
        [
            ("user_01", lambda self: self.user_01),
            ("user_05", lambda self: self.user_05),
            ("tester", lambda self: self.tester),
            ("tenant.owner", lambda self: self.tenant.owner),
        ]
    )
    def test_bugs_new_with_authorized_user_should_work(self, _, get_user):
        user = get_user(self)

        response = self.client.post(
            reverse("bugs-new"),
            {
                "summary": "Test bug",
                "reporter": user.pk,
                "assignee": user.pk,
                "product": self.product.pk,
                "version": self.version.pk,
                "build": self.build.pk,
            },
        )
        self.assertEqual(HTTPStatus.FOUND, response.status_code)

        bug = Bug.objects.last()
        self.assertEqual(bug.summary, "Test bug")
        self.assertEqual(bug.reporter, user)
        self.assertEqual(bug.assignee, user)

    @parameterized.expand(
        [
            ("user_02", lambda self: self.user_02),
            ("user_03", lambda self: self.user_03),
            ("user_04", lambda self: self.user_04),
        ]
    )
    def test_bugs_new_with_unauthorized_user_should_fail(self, _, get_user):
        user = get_user(self)

        response = self.client.post(
            reverse("bugs-new"),
            {
                "summary": "Test bug",
                "reporter": user.pk,
                "assignee": user.pk,
                "product": self.product.pk,
                "version": self.version.pk,
                "build": self.build.pk,
            },
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        self.assertContains(
            response,
            "Select a valid choice.",
        )

    #
    # bugs-edit URL
    #
    @parameterized.expand(
        [
            ("user_01", lambda self: self.user_01),
            ("user_05", lambda self: self.user_05),
            ("tester", lambda self: self.tester),
            ("tenant.owner", lambda self: self.tenant.owner),
        ]
    )
    def test_bugs_edit_with_authorized_user_should_work(self, _, get_user):
        user = get_user(self)

        response = self.client.post(
            reverse("bugs-edit", args=[self.bug.pk]),
            {
                "summary": "Updated bug",
                "reporter": user.pk,
                "assignee": user.pk,
                "product": self.product.pk,
                "version": self.version.pk,
                "build": self.build.pk,
            },
        )
        self.assertEqual(HTTPStatus.FOUND, response.status_code)

        self.bug.refresh_from_db()
        self.assertEqual(self.bug.summary, "Updated bug")
        self.assertEqual(self.bug.reporter, user)
        self.assertEqual(self.bug.assignee, user)

    @parameterized.expand(
        [
            ("user_02", lambda self: self.user_02),
            ("user_03", lambda self: self.user_03),
            ("user_04", lambda self: self.user_04),
        ]
    )
    def test_bugs_edit_with_unauthorized_user_should_fail(self, _, get_user):
        user = get_user(self)

        response = self.client.post(
            reverse("bugs-edit", args=[self.bug.pk]),
            {
                "summary": "Updated bug",
                "reporter": user.pk,
                "assignee": user.pk,
                "product": self.product.pk,
                "version": self.version.pk,
                "build": self.build.pk,
            },
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        self.assertContains(
            response,
            "Select a valid choice.",
        )

    #
    # Bugs.create API method
    #
    @parameterized.expand(
        [
            ("user_01", lambda self: self.user_01),
            ("user_05", lambda self: self.user_05),
            ("tester", lambda self: self.tester),
            ("tenant.owner", lambda self: self.tenant.owner),
        ]
    )
    def test_bugs_create_api_with_authorized_user_should_work(self, _, get_user):
        user = get_user(self)

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "Bug.create",
                "params": [
                    {
                        "summary": "Bug created via API",
                        "reporter": user.pk,
                        "assignee": user.pk,
                        "product": self.product.pk,
                        "version": self.version.pk,
                        "build": self.build.pk,
                    }
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("result", data)
        self.assertEqual(data["result"]["summary"], "Bug created via API")
        self.assertEqual(data["result"]["reporter"], user.pk)
        self.assertEqual(data["result"]["assignee"], user.pk)

    @parameterized.expand(
        [
            ("user_02", lambda self: self.user_02),
            ("user_03", lambda self: self.user_03),
            ("user_04", lambda self: self.user_04),
        ]
    )
    def test_bugs_create_api_with_unauthorized_user_should_fail(self, _, get_user):
        user = get_user(self)

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "Bug.create",
                "params": [
                    {
                        "summary": "Bug created via API",
                        "reporter": user.pk,
                        "assignee": user.pk,
                        "product": self.product.pk,
                        "version": self.version.pk,
                        "build": self.build.pk,
                    }
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("error", data)
        self.assertRegex(
            data["error"]["message"], r"reporter.*Select a valid choice"
        )
