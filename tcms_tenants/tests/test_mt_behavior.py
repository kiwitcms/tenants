# Copyright (c) 2026 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

# pylint: disable=too-many-ancestors, too-many-lines, too-many-public-methods
import json

from http import HTTPStatus

from django.contrib.auth.models import Permission
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from django_tenants import utils
from parameterized import parameterized
from tcms.bugs.models import Bug
from tcms.bugs.tests.factory import BugFactory
from tcms.testcases.models import TestCase
from tcms.testplans.models import TestPlan
from tcms.tests.factories import (
    BuildFactory,
    CategoryFactory,
    ComponentFactory,
    GroupFactory,
    PlanTypeFactory,
    ProductFactory,
    TestCaseFactory,
    TestExecutionFactory,
    TestPlanFactory,
    TestRunFactory,
    VersionFactory,
)
from tcms.testruns.models import TestExecutionStatus, TestRun

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
            cls.category = CategoryFactory(product=cls.product)
            cls.version = VersionFactory(product=cls.product)
            cls.build = BuildFactory(version=cls.version)
            cls.bug = BugFactory(
                reporter=cls.tester,
                assignee=cls.tester,
            )
            cls.plan_type = PlanTypeFactory()
            cls.test_plan = TestPlanFactory(
                author=cls.tester,
                product=cls.product,
                product_version=cls.version,
                type=cls.plan_type,
            )
            cls.test_case = TestCaseFactory(
                author=cls.tester,
                default_tester=cls.tester,
                reviewer=cls.tester,
                category=cls.category,
            )
            cls.case_text_version = 0
            cls.test_run = TestRunFactory(
                plan=cls.test_plan,
                build=cls.build,
                manager=cls.tester,
                default_tester=cls.tester,
            )
            cls.status = TestExecutionStatus.objects.order_by("pk").first()
            cls.test_execution = TestExecutionFactory(
                assignee=cls.tester,
                tested_by=cls.tester,
                run=cls.test_run,
                case=cls.test_case,
                build=cls.build,
                status=cls.status,
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

        # Grant auth.view_user and auth.change_user to self.tester
        # for User.filter, User.update, etc.
        for codename in ("view_user", "change_user"):
            cls.tester.user_permissions.add(
                Permission.objects.get(
                    content_type__app_label="auth",
                    codename=codename,
                )
            )

        # Create a Django auth group for User.join_group tests
        cls.auth_group = GroupFactory()

    def setUp(self):
        for user in (self.tester, self.tenant.owner, self.user_01, self.user_05):
            user.is_active = True
            user.is_staff = True
            user.set_password("password")
            user.save()

        super().setUp()

        # Start each test with a clean CC list
        with utils.tenant_context(self.tenant):
            self.test_run.cc.clear()

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
    def test_component_create_api_with_authorized_user_should_work(
        self, _name, get_user
    ):
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
    def test_component_create_api_with_unauthorized_user_should_fail(
        self, _name, get_user
    ):
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
    def test_component_update_api_with_authorized_user_should_work(
        self, _name, get_user
    ):
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
    def test_component_update_api_with_unauthorized_user_should_fail(
        self, _name, get_user
    ):
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

    @parameterized.expand(
        [
            ("user_01", lambda self: self.user_01),
            ("user_05", lambda self: self.user_05),
            ("tester", lambda self: self.tester),
            ("tenant.owner", lambda self: self.tenant.owner),
        ]
    )
    def test_bugs_new_with_authorized_user_should_work(self, _name, get_user):
        user = get_user(self)

        response = self.client.post(
            reverse("bugs-new"),
            {
                "summary": f"Test bug from {user.username}",
                "reporter": user.pk,
                "assignee": user.pk,
                "product": self.product.pk,
                "version": self.version.pk,
                "build": self.build.pk,
            },
            follow=True,
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        self.assertContains(response, f"Test bug from {user.username}")

        bug = Bug.objects.last()
        self.assertEqual(bug.summary, f"Test bug from {user.username}")
        self.assertEqual(bug.reporter, user)
        self.assertEqual(bug.assignee, user)

    @parameterized.expand(
        [
            ("user_02", lambda self: self.user_02),
            ("user_03", lambda self: self.user_03),
            ("user_04", lambda self: self.user_04),
        ]
    )
    def test_bugs_new_with_unauthorized_user_should_fail(self, _name, get_user):
        user = get_user(self)

        # assignee is unauthorized
        response = self.client.post(
            reverse("bugs-new"),
            {
                "summary": f"Test bug from {user.username}",
                "reporter": self.tester.pk,
                "assignee": user.pk,
                "product": self.product.pk,
                "version": self.version.pk,
                "build": self.build.pk,
            },
            follow=True,
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        self.assertContains(response, "id_assignee_error")
        self.assertContains(response, f'Unknown user_id: "{user.pk}"', html=True)

        # reporter is unauthorized (hidden field, no error reported)
        response = self.client.post(
            reverse("bugs-new"),
            {
                "summary": f"Test bug from {user.username}",
                "reporter": user.pk,
                "assignee": self.tester.pk,
                "product": self.product.pk,
                "version": self.version.pk,
                "build": self.build.pk,
            },
            follow=True,
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        self.assertContains(response, _("New Bug"))

    @parameterized.expand(
        [
            ("user_01", lambda self: self.user_01),
            ("user_05", lambda self: self.user_05),
            ("tester", lambda self: self.tester),
            ("tenant.owner", lambda self: self.tenant.owner),
        ]
    )
    def test_bugs_edit_with_authorized_user_should_work(self, _name, get_user):
        user = get_user(self)

        response = self.client.post(
            reverse("bugs-edit", args=[self.bug.pk]),
            {
                "summary": f"Updated by {user.username}",
                "reporter": user.pk,
                "assignee": user.pk,
                "product": self.product.pk,
                "version": self.version.pk,
                "build": self.build.pk,
            },
            follow=True,
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        self.assertContains(response, f"Updated by {user.username}")

        self.bug.refresh_from_db()
        self.assertEqual(self.bug.summary, f"Updated by {user.username}")
        self.assertEqual(self.bug.reporter, user)
        self.assertEqual(self.bug.assignee, user)

    @parameterized.expand(
        [
            ("user_02", lambda self: self.user_02),
            ("user_03", lambda self: self.user_03),
            ("user_04", lambda self: self.user_04),
        ]
    )
    def test_bugs_edit_with_unauthorized_user_should_fail(self, _name, get_user):
        user = get_user(self)

        # assignee is unauthorized
        response = self.client.post(
            reverse("bugs-edit", args=[self.bug.pk]),
            {
                "summary": f"Updated by {user.username}",
                "reporter": self.tester.pk,
                "assignee": user.pk,
                "product": self.product.pk,
                "version": self.version.pk,
                "build": self.build.pk,
            },
            follow=True,
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        self.assertContains(response, "id_assignee_error")
        self.assertContains(response, f'Unknown user_id: "{user.pk}"', html=True)

        # reporter is unauthorized (hidden field, no error reported)
        response = self.client.post(
            reverse("bugs-edit", args=[self.bug.pk]),
            {
                "summary": f"Updated by {user.username}",
                "reporter": user.pk,
                "assignee": self.tester.pk,
                "product": self.product.pk,
                "version": self.version.pk,
                "build": self.build.pk,
            },
            follow=True,
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        self.assertContains(response, _("Edit bug"))

    @parameterized.expand(
        [
            ("user_01", lambda self: self.user_01),
            ("user_05", lambda self: self.user_05),
            ("tester", lambda self: self.tester),
            ("tenant.owner", lambda self: self.tenant.owner),
        ]
    )
    def test_bugs_create_api_with_authorized_user_should_work(self, _name, get_user):
        user = get_user(self)

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "Bug.create",
                "params": [
                    {
                        "summary": f"Bug created via API by {user.username}",
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
        self.assertEqual(
            data["result"]["summary"], f"Bug created via API by {user.username}"
        )
        self.assertEqual(data["result"]["reporter"], user.pk)
        self.assertEqual(data["result"]["assignee"], user.pk)

    @parameterized.expand(
        [
            ("user_02", lambda self: self.user_02),
            ("user_03", lambda self: self.user_03),
            ("user_04", lambda self: self.user_04),
        ]
    )
    def test_bugs_create_api_with_unauthorized_user_should_fail(self, _name, get_user):
        user = get_user(self)

        # reporter is authorized, assignee is unauthorized
        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "Bug.create",
                "params": [
                    {
                        "summary": f"Bug created via API by {user.username}",
                        "reporter": self.tester.pk,
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
        self.assertRegex(data["error"]["message"], r"assignee.*Unknown user_id")

        # reporter is unauthorized, assignee is authorized
        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "Bug.create",
                "params": [
                    {
                        "summary": f"Bug created via API by {user.username}",
                        "reporter": user.pk,
                        "assignee": self.tester.pk,
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
        self.assertRegex(data["error"]["message"], r"reporter.*Select a valid choice")

    @parameterized.expand(
        [
            ("user_01", lambda self: self.user_01),
            ("user_05", lambda self: self.user_05),
            ("tester", lambda self: self.tester),
            ("tenant.owner", lambda self: self.tenant.owner),
        ]
    )
    def test_plans_new_with_authorized_user_should_work(self, _name, get_user):
        user = get_user(self)

        response = self.client.post(
            reverse("plans-new"),
            {
                "author": user.pk,
                "product": self.product.pk,
                "product_version": self.version.pk,
                "type": self.plan_type.pk,
                "name": f"Test plan from {user.username}",
                "email_settings-0-auto_to_plan_author": "on",
                "email_settings-0-auto_to_case_owner": "on",
                "email_settings-0-auto_to_case_default_tester": "on",
                "email_settings-0-notify_on_case_update": "on",
                "email_settings-0-notify_on_plan_update": "on",
                "email_settings-0-id": self.test_plan.emailing.pk,
                "email_settings-TOTAL_FORMS": "1",
                "email_settings-INITIAL_FORMS": "1",
                "email_settings-MIN_NUM_FORMS": "0",
                "email_settings-MAX_NUM_FORMS": "1",
                "is_active": True,
            },
            follow=True,
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        self.assertContains(response, f"Test plan from {user.username}")

        plan = TestPlan.objects.get(name=f"Test plan from {user.username}")
        self.assertEqual(plan.author, user)

    @parameterized.expand(
        [
            ("user_02", lambda self: self.user_02),
            ("user_03", lambda self: self.user_03),
            ("user_04", lambda self: self.user_04),
        ]
    )
    def test_plans_new_with_unauthorized_user_should_fail(self, _name, get_user):
        user = get_user(self)

        # author is a hidden field, no error reported
        response = self.client.post(
            reverse("plans-new"),
            {
                "author": user.pk,
                "product": self.product.pk,
                "product_version": self.version.pk,
                "type": self.plan_type.pk,
                "name": f"Test plan from {user.username}",
                "email_settings-0-auto_to_plan_author": "on",
                "email_settings-0-auto_to_case_owner": "on",
                "email_settings-0-auto_to_case_default_tester": "on",
                "email_settings-0-notify_on_case_update": "on",
                "email_settings-0-notify_on_plan_update": "on",
                "email_settings-0-id": self.test_plan.emailing.pk,
                "email_settings-TOTAL_FORMS": "1",
                "email_settings-INITIAL_FORMS": "1",
                "email_settings-MIN_NUM_FORMS": "0",
                "email_settings-MAX_NUM_FORMS": "1",
                "is_active": True,
            },
            follow=True,
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        self.assertContains(response, _("Create new TestPlan"))

    @parameterized.expand(
        [
            ("user_01", lambda self: self.user_01),
            ("user_05", lambda self: self.user_05),
            ("tester", lambda self: self.tester),
            ("tenant.owner", lambda self: self.tenant.owner),
        ]
    )
    def test_plans_edit_with_authorized_user_should_work(self, _name, get_user):
        user = get_user(self)

        response = self.client.post(
            reverse("plan-edit", args=[self.test_plan.pk]),
            {
                "author": user.pk,
                "product": self.product.pk,
                "product_version": self.version.pk,
                "type": self.plan_type.pk,
                "name": f"Updated by {user.username}",
                "email_settings-0-auto_to_plan_author": "on",
                "email_settings-0-auto_to_case_owner": "on",
                "email_settings-0-auto_to_case_default_tester": "on",
                "email_settings-0-notify_on_case_update": "on",
                "email_settings-0-notify_on_plan_update": "on",
                "email_settings-0-id": self.test_plan.emailing.pk,
                "email_settings-TOTAL_FORMS": "1",
                "email_settings-INITIAL_FORMS": "1",
                "email_settings-MIN_NUM_FORMS": "0",
                "email_settings-MAX_NUM_FORMS": "1",
                "is_active": True,
            },
            follow=True,
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        self.assertContains(response, f"Updated by {user.username}")

        self.test_plan.refresh_from_db()
        self.assertEqual(self.test_plan.author, user)
        self.assertEqual(self.test_plan.name, f"Updated by {user.username}")

    @parameterized.expand(
        [
            ("user_02", lambda self: self.user_02),
            ("user_03", lambda self: self.user_03),
            ("user_04", lambda self: self.user_04),
        ]
    )
    def test_plans_edit_with_unauthorized_user_should_fail(self, _name, get_user):
        user = get_user(self)

        # author is a hidden field, no error reported
        response = self.client.post(
            reverse("plan-edit", args=[self.test_plan.pk]),
            {
                "author": user.pk,
                "product": self.product.pk,
                "product_version": self.version.pk,
                "type": self.plan_type.pk,
                "name": f"Updated by {user.username}",
                "email_settings-0-auto_to_plan_author": "on",
                "email_settings-0-auto_to_case_owner": "on",
                "email_settings-0-auto_to_case_default_tester": "on",
                "email_settings-0-notify_on_case_update": "on",
                "email_settings-0-notify_on_plan_update": "on",
                "email_settings-0-id": self.test_plan.emailing.pk,
                "email_settings-TOTAL_FORMS": "1",
                "email_settings-INITIAL_FORMS": "1",
                "email_settings-MIN_NUM_FORMS": "0",
                "email_settings-MAX_NUM_FORMS": "1",
                "is_active": True,
            },
            follow=True,
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        self.assertContains(response, _("Edit TestPlan"))

    @parameterized.expand(
        [
            ("user_01", lambda self: self.user_01),
            ("user_05", lambda self: self.user_05),
            ("tester", lambda self: self.tester),
            ("tenant.owner", lambda self: self.tenant.owner),
        ]
    )
    def test_plans_create_api_with_authorized_user_should_work(self, _name, get_user):
        user = get_user(self)

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TestPlan.create",
                "params": [
                    {
                        "product": self.product.pk,
                        "product_version": self.version.pk,
                        "type": self.plan_type.pk,
                        "name": f"TestPlan created via API by {user.username}",
                        "author": user.pk,
                        "is_active": True,
                    }
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("result", data)
        self.assertEqual(
            data["result"]["name"], f"TestPlan created via API by {user.username}"
        )
        self.assertEqual(data["result"]["author"], user.pk)

    @parameterized.expand(
        [
            ("user_02", lambda self: self.user_02),
            ("user_03", lambda self: self.user_03),
            ("user_04", lambda self: self.user_04),
        ]
    )
    def test_plans_create_api_with_unauthorized_user_should_fail(self, _name, get_user):
        user = get_user(self)

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TestPlan.create",
                "params": [
                    {
                        "product": self.product.pk,
                        "product_version": self.version.pk,
                        "type": self.plan_type.pk,
                        "name": f"TestPlan created via API by {user.username}",
                        "author": user.pk,
                        "is_active": True,
                    }
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("error", data)
        self.assertRegex(data["error"]["message"], r"author.*Select a valid choice")

    @parameterized.expand(
        [
            ("user_01", lambda self: self.user_01),
            ("user_05", lambda self: self.user_05),
            ("tester", lambda self: self.tester),
            ("tenant.owner", lambda self: self.tenant.owner),
        ]
    )
    def test_plans_update_api_with_authorized_user_should_work(self, _name, get_user):
        user = get_user(self)

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TestPlan.update",
                "params": [
                    self.test_plan.pk,
                    {
                        "author": user.pk,
                    },
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("result", data)
        self.assertEqual(data["result"]["author"], user.pk)

    @parameterized.expand(
        [
            ("user_02", lambda self: self.user_02),
            ("user_03", lambda self: self.user_03),
            ("user_04", lambda self: self.user_04),
        ]
    )
    def test_plans_update_api_with_unauthorized_user_should_fail(self, _name, get_user):
        user = get_user(self)

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TestPlan.update",
                "params": [
                    self.test_plan.pk,
                    {
                        "author": user.pk,
                    },
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("error", data)
        self.assertRegex(data["error"]["message"], r"author.*Select a valid choice")

    @parameterized.expand(
        [
            ("user_01", lambda self: self.user_01),
            ("user_05", lambda self: self.user_05),
            ("tester", lambda self: self.tester),
            ("tenant.owner", lambda self: self.tenant.owner),
        ]
    )
    def test_testexecution_create_api_with_authorized_user_should_work(
        self, _name, get_user
    ):
        user = get_user(self)

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TestExecution.create",
                "params": [
                    {
                        "assignee": user.pk,
                        "tested_by": user.pk,
                        "run": self.test_run.pk,
                        "case": self.test_case.pk,
                        "case_text_version": self.case_text_version,
                        "build": self.build.pk,
                        "status": self.status.pk,
                    }
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("result", data)
        self.assertEqual(data["result"]["assignee"], user.pk)
        self.assertEqual(data["result"]["tested_by"], user.pk)

    @parameterized.expand(
        [
            ("user_02", lambda self: self.user_02),
            ("user_03", lambda self: self.user_03),
            ("user_04", lambda self: self.user_04),
        ]
    )
    def test_testexecution_create_api_with_unauthorized_user_should_fail(
        self, _name, get_user
    ):
        user = get_user(self)

        # assignee is unauthorized
        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TestExecution.create",
                "params": [
                    {
                        "assignee": user.pk,
                        "tested_by": self.tester.pk,
                        "run": self.test_run.pk,
                        "case": self.test_case.pk,
                        "case_text_version": self.case_text_version,
                        "build": self.build.pk,
                        "status": self.status.pk,
                    }
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("error", data)
        self.assertRegex(data["error"]["message"], r"assignee.*Unknown user_id")

        # tested_by is unauthorized
        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TestExecution.create",
                "params": [
                    {
                        "assignee": self.tester.pk,
                        "tested_by": user.pk,
                        "run": self.test_run.pk,
                        "case": self.test_case.pk,
                        "case_text_version": self.case_text_version,
                        "build": self.build.pk,
                        "status": self.status.pk,
                    }
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("error", data)
        self.assertRegex(data["error"]["message"], r"tested_by.*Unknown user_id")

    @parameterized.expand(
        [
            ("user_01", lambda self: self.user_01),
            ("user_05", lambda self: self.user_05),
            ("tester", lambda self: self.tester),
            ("tenant.owner", lambda self: self.tenant.owner),
        ]
    )
    def test_testexecution_update_api_with_authorized_user_should_work(
        self, _name, get_user
    ):
        user = get_user(self)

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TestExecution.update",
                "params": [
                    self.test_execution.pk,
                    {
                        "assignee": user.pk,
                        "tested_by": user.pk,
                    },
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("result", data)
        self.assertEqual(data["result"]["assignee"], user.pk)
        self.assertEqual(data["result"]["tested_by"], user.pk)

        self.test_execution.refresh_from_db()
        self.assertEqual(self.test_execution.assignee, user)
        self.assertEqual(self.test_execution.tested_by, user)

    @parameterized.expand(
        [
            ("user_02", lambda self: self.user_02),
            ("user_03", lambda self: self.user_03),
            ("user_04", lambda self: self.user_04),
        ]
    )
    def test_testexecution_update_api_with_unauthorized_user_should_fail(
        self, _name, get_user
    ):
        user = get_user(self)

        # assignee is unauthorized
        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TestExecution.update",
                "params": [
                    self.test_execution.pk,
                    {
                        "assignee": user.pk,
                    },
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("error", data)
        self.assertRegex(data["error"]["message"], r"assignee.*Unknown user_id")

        # tested_by is unauthorized
        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TestExecution.update",
                "params": [
                    self.test_execution.pk,
                    {
                        "tested_by": user.pk,
                    },
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("error", data)
        self.assertRegex(data["error"]["message"], r"tested_by.*Unknown user_id")

    @parameterized.expand(
        [
            ("user_01", lambda self: self.user_01),
            ("user_05", lambda self: self.user_05),
            ("tester", lambda self: self.tester),
            ("tenant.owner", lambda self: self.tenant.owner),
        ]
    )
    def test_testrun_create_api_with_authorized_user_should_work(self, _name, get_user):
        user = get_user(self)

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TestRun.create",
                "params": [
                    {
                        "build": self.build.pk,
                        "plan": self.test_plan.pk,
                        "summary": f"TestRun created via API by {user.username}",
                        "manager": user.pk,
                        "default_tester": user.pk,
                    }
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("result", data)
        self.assertEqual(
            data["result"]["summary"],
            f"TestRun created via API by {user.username}",
        )
        self.assertEqual(data["result"]["manager"], user.pk)
        self.assertEqual(data["result"]["default_tester"], user.pk)

    @parameterized.expand(
        [
            ("user_02", lambda self: self.user_02),
            ("user_03", lambda self: self.user_03),
            ("user_04", lambda self: self.user_04),
        ]
    )
    def test_testrun_create_api_with_unauthorized_user_should_fail(
        self, _name, get_user
    ):
        user = get_user(self)

        # manager is unauthorized, default_tester is authorized
        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TestRun.create",
                "params": [
                    {
                        "build": self.build.pk,
                        "plan": self.test_plan.pk,
                        "summary": f"TestRun created via API by {user.username}",
                        "manager": user.pk,
                        "default_tester": self.tester.pk,
                    }
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("error", data)
        self.assertRegex(data["error"]["message"], r"manager.*Unknown user_id")

        # default_tester is unauthorized, manager is authorized
        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TestRun.create",
                "params": [
                    {
                        "build": self.build.pk,
                        "plan": self.test_plan.pk,
                        "summary": f"TestRun created via API by {user.username}",
                        "manager": self.tester.pk,
                        "default_tester": user.pk,
                    }
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("error", data)
        self.assertRegex(data["error"]["message"], r"default_tester.*Unknown user_id")

    @parameterized.expand(
        [
            ("user_01", lambda self: self.user_01),
            ("user_05", lambda self: self.user_05),
            ("tester", lambda self: self.tester),
            ("tenant.owner", lambda self: self.tenant.owner),
        ]
    )
    def test_testrun_update_api_with_authorized_user_should_work(self, _name, get_user):
        user = get_user(self)

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TestRun.update",
                "params": [
                    self.test_run.pk,
                    {
                        "manager": user.pk,
                        "default_tester": user.pk,
                    },
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("result", data)
        self.assertEqual(data["result"]["manager"], user.pk)
        self.assertEqual(data["result"]["default_tester"], user.pk)

        self.test_run.refresh_from_db()
        self.assertEqual(self.test_run.manager, user)
        self.assertEqual(self.test_run.default_tester, user)

    @parameterized.expand(
        [
            ("user_02", lambda self: self.user_02),
            ("user_03", lambda self: self.user_03),
            ("user_04", lambda self: self.user_04),
        ]
    )
    def test_testrun_update_api_with_unauthorized_user_should_fail(
        self, _name, get_user
    ):
        user = get_user(self)

        # manager is unauthorized
        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TestRun.update",
                "params": [
                    self.test_run.pk,
                    {
                        "manager": user.pk,
                    },
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("error", data)
        self.assertRegex(data["error"]["message"], r"manager.*Unknown user_id")

        # default_tester is unauthorized
        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TestRun.update",
                "params": [
                    self.test_run.pk,
                    {
                        "default_tester": user.pk,
                    },
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("error", data)
        self.assertRegex(data["error"]["message"], r"default_tester.*Unknown user_id")

    @parameterized.expand(
        [
            ("user_01", lambda self: self.user_01),
            ("user_05", lambda self: self.user_05),
            ("tester", lambda self: self.tester),
            ("tenant.owner", lambda self: self.tenant.owner),
        ]
    )
    def test_testruns_new_with_authorized_user_should_work(self, _name, get_user):
        user = get_user(self)

        response = self.client.post(
            reverse("testruns-new"),
            {
                "summary": f"Test run from {user.username}",
                "manager": user.pk,
                "default_tester": user.pk,
                "product": self.product.pk,
                "plan": self.test_plan.pk,
                "build": self.build.pk,
            },
            follow=True,
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        self.assertContains(response, f"Test run from {user.username}")

        test_run = TestRun.objects.get(summary=f"Test run from {user.username}")
        self.assertEqual(test_run.manager, user)
        self.assertEqual(test_run.default_tester, user)

    @parameterized.expand(
        [
            ("user_02", lambda self: self.user_02),
            ("user_03", lambda self: self.user_03),
            ("user_04", lambda self: self.user_04),
        ]
    )
    def test_testruns_new_with_unauthorized_user_should_fail(self, _name, get_user):
        user = get_user(self)

        # manager is unauthorized, default_tester is authorized
        response = self.client.post(
            reverse("testruns-new"),
            {
                "summary": f"Test run from {user.username}",
                "manager": user.pk,
                "default_tester": self.tester.pk,
                "product": self.product.pk,
                "plan": self.test_plan.pk,
                "build": self.build.pk,
            },
            follow=True,
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        self.assertContains(response, "id_manager_error")
        self.assertContains(response, f'Unknown user_id: "{user.pk}"', html=True)

        # default_tester is unauthorized, manager is authorized
        response = self.client.post(
            reverse("testruns-new"),
            {
                "summary": f"Test run from {user.username}",
                "manager": self.tester.pk,
                "default_tester": user.pk,
                "product": self.product.pk,
                "plan": self.test_plan.pk,
                "build": self.build.pk,
            },
            follow=True,
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        self.assertContains(response, "id_default_tester_error")
        self.assertContains(response, f'Unknown user_id: "{user.pk}"', html=True)

    @parameterized.expand(
        [
            ("user_01", lambda self: self.user_01),
            ("user_05", lambda self: self.user_05),
            ("tester", lambda self: self.tester),
            ("tenant.owner", lambda self: self.tenant.owner),
        ]
    )
    def test_testruns_edit_with_authorized_user_should_work(self, _name, get_user):
        user = get_user(self)

        response = self.client.post(
            reverse("testruns-edit", args=[self.test_run.pk]),
            {
                "summary": f"Updated by {user.username}",
                "manager": user.pk,
                "default_tester": user.pk,
                "product": self.product.pk,
                "plan": self.test_plan.pk,
                "build": self.build.pk,
            },
            follow=True,
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        self.assertContains(response, f"Updated by {user.username}")

        self.test_run.refresh_from_db()
        self.assertEqual(self.test_run.summary, f"Updated by {user.username}")
        self.assertEqual(self.test_run.manager, user)
        self.assertEqual(self.test_run.default_tester, user)

    @parameterized.expand(
        [
            ("user_02", lambda self: self.user_02),
            ("user_03", lambda self: self.user_03),
            ("user_04", lambda self: self.user_04),
        ]
    )
    def test_testruns_edit_with_unauthorized_user_should_fail(self, _name, get_user):
        user = get_user(self)

        # manager is unauthorized
        response = self.client.post(
            reverse("testruns-edit", args=[self.test_run.pk]),
            {
                "summary": f"Updated by {user.username}",
                "manager": user.pk,
                "default_tester": self.tester.pk,
                "product": self.product.pk,
                "plan": self.test_plan.pk,
                "build": self.build.pk,
            },
            follow=True,
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        self.assertContains(response, "id_manager_error")
        self.assertContains(response, f'Unknown user_id: "{user.pk}"', html=True)

        # default_tester is unauthorized
        response = self.client.post(
            reverse("testruns-edit", args=[self.test_run.pk]),
            {
                "summary": f"Updated by {user.username}",
                "manager": self.tester.pk,
                "default_tester": user.pk,
                "product": self.product.pk,
                "plan": self.test_plan.pk,
                "build": self.build.pk,
            },
            follow=True,
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        self.assertContains(response, "id_default_tester_error")
        self.assertContains(response, f'Unknown user_id: "{user.pk}"', html=True)

    @parameterized.expand(
        [
            ("user_01", lambda self: self.user_01),
            ("user_05", lambda self: self.user_05),
            ("tester", lambda self: self.tester),
            ("tenant.owner", lambda self: self.tenant.owner),
        ]
    )
    def test_testcase_create_api_with_authorized_user_should_work(
        self, _name, get_user
    ):
        user = get_user(self)

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TestCase.create",
                "params": [
                    {
                        "author": user.pk,
                        "default_tester": user.pk,
                        "product": self.product.pk,
                        "category": self.category.pk,
                        "priority": self.test_case.priority.pk,
                        "case_status": self.test_case.case_status.pk,
                        "summary": f"TestCase created via API by {user.username}",
                        "text": "Given-When-Then",
                    }
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("result", data)
        self.assertEqual(
            data["result"]["summary"], f"TestCase created via API by {user.username}"
        )
        self.assertEqual(data["result"]["author"], user.pk)
        self.assertEqual(data["result"]["default_tester"], user.pk)

    @parameterized.expand(
        [
            ("user_02", lambda self: self.user_02),
            ("user_03", lambda self: self.user_03),
            ("user_04", lambda self: self.user_04),
        ]
    )
    def test_testcase_create_api_with_unauthorized_user_should_fail(
        self, _name, get_user
    ):
        user = get_user(self)

        # author is unauthorized, default_tester is authorized
        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TestCase.create",
                "params": [
                    {
                        "author": user.pk,
                        "default_tester": self.tester.pk,
                        "product": self.product.pk,
                        "category": self.category.pk,
                        "priority": self.test_case.priority.pk,
                        "case_status": self.test_case.case_status.pk,
                        "summary": f"TestCase created via API by {user.username}",
                        "text": "Given-When-Then",
                    }
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("error", data)
        self.assertRegex(data["error"]["message"], r"author.*Select a valid choice")

        # default_tester is unauthorized, author is authorized
        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TestCase.create",
                "params": [
                    {
                        "author": self.tester.pk,
                        "default_tester": user.pk,
                        "product": self.product.pk,
                        "category": self.category.pk,
                        "priority": self.test_case.priority.pk,
                        "case_status": self.test_case.case_status.pk,
                        "summary": f"TestCase created via API by {user.username}",
                        "text": "Given-When-Then",
                    }
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("error", data)
        self.assertRegex(
            data["error"]["message"], r"default_tester.*Select a valid choice"
        )

    @parameterized.expand(
        [
            ("user_01", lambda self: self.user_01),
            ("user_05", lambda self: self.user_05),
            ("tester", lambda self: self.tester),
            ("tenant.owner", lambda self: self.tenant.owner),
        ]
    )
    def test_testcase_update_api_with_authorized_user_should_work(
        self, _name, get_user
    ):
        user = get_user(self)

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TestCase.update",
                "params": [
                    self.test_case.pk,
                    {
                        "author": user.pk,
                        "default_tester": user.pk,
                        "reviewer": user.pk,
                    },
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("result", data)
        self.assertEqual(data["result"]["author"], user.pk)
        self.assertEqual(data["result"]["default_tester"], user.pk)
        self.assertEqual(data["result"]["reviewer"], user.pk)

        self.test_case.refresh_from_db()
        self.assertEqual(self.test_case.author, user)
        self.assertEqual(self.test_case.default_tester, user)
        self.assertEqual(self.test_case.reviewer, user)

    @parameterized.expand(
        [
            ("user_02", lambda self: self.user_02),
            ("user_03", lambda self: self.user_03),
            ("user_04", lambda self: self.user_04),
        ]
    )
    def test_testcase_update_api_with_unauthorized_user_should_fail(
        self, _name, get_user
    ):
        user = get_user(self)

        # author is unauthorized
        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TestCase.update",
                "params": [
                    self.test_case.pk,
                    {
                        "author": user.pk,
                    },
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("error", data)
        self.assertRegex(data["error"]["message"], r"author.*Unknown user_id")

        # default_tester is unauthorized
        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TestCase.update",
                "params": [
                    self.test_case.pk,
                    {
                        "default_tester": user.pk,
                    },
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("error", data)
        self.assertRegex(data["error"]["message"], r"default_tester.*Unknown user_id")

        # reviewer is unauthorized
        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TestCase.update",
                "params": [
                    self.test_case.pk,
                    {
                        "reviewer": user.pk,
                    },
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("error", data)
        self.assertRegex(data["error"]["message"], r"reviewer.*Unknown user_id")

    @parameterized.expand(
        [
            ("user_01", lambda self: self.user_01),
            ("user_05", lambda self: self.user_05),
            ("tester", lambda self: self.tester),
            ("tenant.owner", lambda self: self.tenant.owner),
        ]
    )
    def test_testcases_new_with_authorized_user_should_work(self, _name, get_user):
        user = get_user(self)

        response = self.client.post(
            reverse("testcases-new"),
            {
                "author": user.pk,
                "default_tester": user.pk,
                "product": self.product.pk,
                "category": self.category.pk,
                "priority": self.test_case.priority.pk,
                "case_status": self.test_case.case_status.pk,
                "summary": f"Test case from {user.username}",
                "setup_duration": "2 20:10:00",
                "testing_duration": "00:00:00",
                "text": "Given-When-Then",
                "script": "some script",
                "arguments": "args1, args2, args3",
                "requirement": "requirement",
                "extra_link": "http://somelink.net",
                "notes": "notes",
                "email_settings-TOTAL_FORMS": "0",
                "email_settings-INITIAL_FORMS": "0",
                "email_settings-MIN_NUM_FORMS": "0",
                "email_settings-MAX_NUM_FORMS": "1",
            },
            follow=True,
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        self.assertContains(response, f"Test case from {user.username}")

        test_case = TestCase.objects.get(summary=f"Test case from {user.username}")
        self.assertEqual(test_case.author, user)
        self.assertEqual(test_case.default_tester, user)

    @parameterized.expand(
        [
            ("user_02", lambda self: self.user_02),
            ("user_03", lambda self: self.user_03),
            ("user_04", lambda self: self.user_04),
        ]
    )
    def test_testcases_new_with_unauthorized_user_should_fail(self, _name, get_user):
        user = get_user(self)

        # author is a hidden field, no error reported
        response = self.client.post(
            reverse("testcases-new"),
            {
                "author": user.pk,
                "default_tester": self.tester.pk,
                "product": self.product.pk,
                "category": self.category.pk,
                "priority": self.test_case.priority.pk,
                "case_status": self.test_case.case_status.pk,
                "summary": f"Test case from {user.username}",
                "setup_duration": "2 20:10:00",
                "testing_duration": "00:00:00",
                "text": "Given-When-Then",
                "script": "some script",
                "arguments": "args1, args2, args3",
                "requirement": "requirement",
                "extra_link": "http://somelink.net",
                "notes": "notes",
            },
            follow=True,
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        self.assertContains(response, _("New Test Case"))

        # default_tester is a visible UserField
        response = self.client.post(
            reverse("testcases-new"),
            {
                "author": self.tester.pk,
                "default_tester": user.pk,
                "product": self.product.pk,
                "category": self.category.pk,
                "priority": self.test_case.priority.pk,
                "case_status": self.test_case.case_status.pk,
                "summary": f"Test case from {user.username}",
                "setup_duration": "2 20:10:00",
                "testing_duration": "00:00:00",
                "text": "Given-When-Then",
                "script": "some script",
                "arguments": "args1, args2, args3",
                "requirement": "requirement",
                "extra_link": "http://somelink.net",
                "notes": "notes",
            },
            follow=True,
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        self.assertContains(response, "id_default_tester_error")
        self.assertContains(response, f'Unknown user_id: "{user.pk}"', html=True)

    @parameterized.expand(
        [
            ("user_01", lambda self: self.user_01),
            ("user_05", lambda self: self.user_05),
            ("tester", lambda self: self.tester),
            ("tenant.owner", lambda self: self.tenant.owner),
        ]
    )
    def test_testcases_edit_with_authorized_user_should_work(self, _name, get_user):
        user = get_user(self)

        response = self.client.post(
            reverse("testcases-edit", args=[self.test_case.pk]),
            {
                "author": user.pk,
                "default_tester": user.pk,
                "product": self.product.pk,
                "category": self.category.pk,
                "priority": self.test_case.priority.pk,
                "case_status": self.test_case.case_status.pk,
                "summary": f"Updated by {user.username}",
                "setup_duration": "2 20:10:00",
                "testing_duration": "00:00:00",
                "text": "Given-When-Then",
                "script": "some script",
                "arguments": "args1, args2, args3",
                "requirement": "requirement",
                "extra_link": "http://somelink.net",
                "notes": "notes",
                "email_settings-0-auto_to_case_author": "on",
                "email_settings-0-auto_to_run_manager": "on",
                "email_settings-0-auto_to_execution_assignee": "on",
                "email_settings-0-auto_to_case_tester": "on",
                "email_settings-0-auto_to_run_tester": "on",
                "email_settings-0-notify_on_case_update": "on",
                "email_settings-0-notify_on_case_delete": "on",
                "email_settings-0-cc_list": "info@example.com",
                "email_settings-0-case": self.test_case.pk,
                "email_settings-0-id": self.test_case.emailing.pk,
                "email_settings-TOTAL_FORMS": "1",
                "email_settings-INITIAL_FORMS": "1",
                "email_settings-MIN_NUM_FORMS": "0",
                "email_settings-MAX_NUM_FORMS": "1",
            },
            follow=True,
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        self.assertContains(response, f"Updated by {user.username}")

        self.test_case.refresh_from_db()
        self.assertEqual(self.test_case.summary, f"Updated by {user.username}")
        self.assertEqual(self.test_case.author, user)
        self.assertEqual(self.test_case.default_tester, user)

    @parameterized.expand(
        [
            ("user_02", lambda self: self.user_02),
            ("user_03", lambda self: self.user_03),
            ("user_04", lambda self: self.user_04),
        ]
    )
    def test_testcases_edit_with_unauthorized_user_should_fail(self, _name, get_user):
        user = get_user(self)

        # author is a hidden field, no error reported
        response = self.client.post(
            reverse("testcases-edit", args=[self.test_case.pk]),
            {
                "author": user.pk,
                "default_tester": self.tester.pk,
                "product": self.product.pk,
                "category": self.category.pk,
                "priority": self.test_case.priority.pk,
                "case_status": self.test_case.case_status.pk,
                "summary": f"Updated by {user.username}",
                "setup_duration": "2 20:10:00",
                "testing_duration": "00:00:00",
                "text": "Given-When-Then",
                "script": "some script",
                "arguments": "args1, args2, args3",
                "requirement": "requirement",
                "extra_link": "http://somelink.net",
                "notes": "notes",
                "email_settings-0-auto_to_case_author": "on",
                "email_settings-0-auto_to_run_manager": "on",
                "email_settings-0-auto_to_execution_assignee": "on",
                "email_settings-0-auto_to_case_tester": "on",
                "email_settings-0-auto_to_run_tester": "on",
                "email_settings-0-notify_on_case_update": "on",
                "email_settings-0-notify_on_case_delete": "on",
                "email_settings-0-cc_list": "info@example.com",
                "email_settings-0-case": self.test_case.pk,
                "email_settings-0-id": self.test_case.emailing.pk,
                "email_settings-TOTAL_FORMS": "1",
                "email_settings-INITIAL_FORMS": "1",
                "email_settings-MIN_NUM_FORMS": "0",
                "email_settings-MAX_NUM_FORMS": "1",
            },
            follow=True,
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        self.assertContains(response, _("Edit TestCase"))

        # default_tester is a visible UserField
        response = self.client.post(
            reverse("testcases-edit", args=[self.test_case.pk]),
            {
                "author": self.tester.pk,
                "default_tester": user.pk,
                "product": self.product.pk,
                "category": self.category.pk,
                "priority": self.test_case.priority.pk,
                "case_status": self.test_case.case_status.pk,
                "summary": f"Updated by {user.username}",
                "setup_duration": "2 20:10:00",
                "testing_duration": "00:00:00",
                "text": "Given-When-Then",
                "script": "some script",
                "arguments": "args1, args2, args3",
                "requirement": "requirement",
                "extra_link": "http://somelink.net",
                "notes": "notes",
                "email_settings-0-auto_to_case_author": "on",
                "email_settings-0-auto_to_run_manager": "on",
                "email_settings-0-auto_to_execution_assignee": "on",
                "email_settings-0-auto_to_case_tester": "on",
                "email_settings-0-auto_to_run_tester": "on",
                "email_settings-0-notify_on_case_update": "on",
                "email_settings-0-notify_on_case_delete": "on",
                "email_settings-0-cc_list": "info@example.com",
                "email_settings-0-case": self.test_case.pk,
                "email_settings-0-id": self.test_case.emailing.pk,
                "email_settings-TOTAL_FORMS": "1",
                "email_settings-INITIAL_FORMS": "1",
                "email_settings-MIN_NUM_FORMS": "0",
                "email_settings-MAX_NUM_FORMS": "1",
            },
            follow=True,
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        self.assertContains(response, "id_default_tester_error")
        self.assertContains(response, f'Unknown user_id: "{user.pk}"', html=True)

    def test_user_filter_returns_only_authorized_users(self):
        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "User.filter",
                "params": [{"is_active": True}],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("result", data)

        result_ids = {user["id"] for user in data["result"]}

        for user in (self.tester, self.tenant.owner, self.user_01, self.user_05):
            self.assertIn(
                user.pk,
                result_ids,
                f"Authorized user pk={user.pk} should be in User.filter result",
            )

        for user in (self.user_02, self.user_03, self.user_04):
            self.assertNotIn(
                user.pk,
                result_ids,
                f"Unauthorized user pk={user.pk} should NOT be in User.filter result",
            )

    @parameterized.expand(
        [
            ("user_01", lambda self: self.user_01),
            ("user_05", lambda self: self.user_05),
            ("tester", lambda self: self.tester),
            ("tenant.owner", lambda self: self.tenant.owner),
        ]
    )
    def test_user_update_api_with_authorized_user_should_work(self, _name, get_user):
        user = get_user(self)

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "User.update",
                "params": [
                    user.pk,
                    {"first_name": f"Changed by {user.pk}"},
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("result", data)
        self.assertEqual(data["result"]["first_name"], f"Changed by {user.pk}")

        user.refresh_from_db()
        self.assertEqual(user.first_name, f"Changed by {user.pk}")

    @parameterized.expand(
        [
            ("user_02", lambda self: self.user_02),
            ("user_03", lambda self: self.user_03),
            ("user_04", lambda self: self.user_04),
        ]
    )
    def test_user_update_api_with_unauthorized_user_should_fail(self, _name, get_user):
        user = get_user(self)
        original_first_name = user.first_name

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "User.update",
                "params": [
                    user.pk,
                    {"first_name": f"Changed by {user.pk}"},
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("error", data)
        self.assertIn("User matching query does not exist", data["error"]["message"])

        user.refresh_from_db()
        self.assertEqual(user.first_name, original_first_name)

    @parameterized.expand(
        [
            ("user_01", lambda self: self.user_01),
            ("user_05", lambda self: self.user_05),
            ("tester", lambda self: self.tester),
            ("tenant.owner", lambda self: self.tenant.owner),
        ]
    )
    def test_user_deactivate_api_with_authorized_user_should_work(
        self, _name, get_user
    ):
        user = get_user(self)

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "User.deactivate",
                "params": [{"pk": user.pk}],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("result", data)
        self.assertEqual(len(data["result"]), 1)
        self.assertEqual(data["result"][0]["id"], user.pk)

        user.refresh_from_db()
        self.assertFalse(user.is_active)

    @parameterized.expand(
        [
            ("user_02", lambda self: self.user_02),
            ("user_03", lambda self: self.user_03),
            ("user_04", lambda self: self.user_04),
        ]
    )
    def test_user_deactivate_api_with_unauthorized_user_should_noop(
        self, _name, get_user
    ):
        user = get_user(self)

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "User.deactivate",
                "params": [{"pk": user.pk}],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertEqual(data["result"], [])

        user.refresh_from_db()
        self.assertTrue(user.is_active)

    @parameterized.expand(
        [
            ("user_01", lambda self: self.user_01),
            ("user_05", lambda self: self.user_05),
            ("tester", lambda self: self.tester),
            ("tenant.owner", lambda self: self.tenant.owner),
        ]
    )
    def test_user_join_group_api_with_authorized_user_should_work(
        self, _name, get_user
    ):
        user = get_user(self)

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "User.join_group",
                "params": [user.username, self.auth_group.name],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("result", data)

        user.refresh_from_db()
        self.assertTrue(user.groups.filter(name=self.auth_group.name).exists())

    @parameterized.expand(
        [
            ("user_02", lambda self: self.user_02),
            ("user_03", lambda self: self.user_03),
            ("user_04", lambda self: self.user_04),
        ]
    )
    def test_user_join_group_api_with_unauthorized_user_should_fail(
        self, _name, get_user
    ):
        user = get_user(self)

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "User.join_group",
                "params": [user.username, self.auth_group.name],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("error", data)
        self.assertIn("User matching query does not exist", data["error"]["message"])

        user.refresh_from_db()
        self.assertFalse(user.groups.filter(name=self.auth_group.name).exists())

    @parameterized.expand(
        [
            ("user_01", lambda self: self.user_01),
            ("user_05", lambda self: self.user_05),
            ("tester", lambda self: self.tester),
            ("tenant.owner", lambda self: self.tenant.owner),
        ]
    )
    def test_testrun_add_cc_with_authorized_users_should_work(self, _name, get_user):
        user = get_user(self)

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TestRun.add_cc",
                "params": [self.test_run.pk, user.pk],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("result", data)

        self.test_run.refresh_from_db()
        self.assertTrue(self.test_run.cc.filter(pk=user.pk).exists())

    @parameterized.expand(
        [
            ("user_02", lambda self: self.user_02),
            ("user_03", lambda self: self.user_03),
            ("user_04", lambda self: self.user_04),
        ]
    )
    def test_testrun_add_cc_with_unauthorized_users_should_fail(self, _name, get_user):
        user = get_user(self)

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TestRun.add_cc",
                "params": [self.test_run.pk, user.pk],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("error", data)
        self.assertRegex(data["error"]["message"], r"user.*Unknown user_id")

        self.test_run.refresh_from_db()
        self.assertFalse(self.test_run.cc.filter(pk=user.pk).exists())

    @parameterized.expand(
        [
            ("user_01", lambda self: self.user_01),
            ("user_05", lambda self: self.user_05),
            ("tester", lambda self: self.tester),
            ("tenant.owner", lambda self: self.tenant.owner),
        ]
    )
    def test_testrun_remove_cc_with_authorized_users_should_work(self, _name, get_user):
        user = get_user(self)

        # First add the user as CC so we have something to remove
        self.test_run.add_cc(user)
        self.test_run.refresh_from_db()
        self.assertTrue(self.test_run.cc.filter(pk=user.pk).exists())

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TestRun.remove_cc",
                "params": [self.test_run.pk, user.pk],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("result", data)

        self.test_run.refresh_from_db()
        self.assertFalse(self.test_run.cc.filter(pk=user.pk).exists())

    @parameterized.expand(
        [
            ("user_02", lambda self: self.user_02),
            ("user_03", lambda self: self.user_03),
            ("user_04", lambda self: self.user_04),
        ]
    )
    def test_testrun_remove_cc_with_unauthorized_users_should_fail(
        self, _name, get_user
    ):
        user = get_user(self)

        # cc list is already empty from setUp

        response = self.client.post(
            "/json-rpc/",
            {
                "id": "jsonrpc",
                "jsonrpc": "2.0",
                "method": "TestRun.remove_cc",
                "params": [self.test_run.pk, user.pk],
            },
            content_type="application/json",
        )
        self.assertEqual(HTTPStatus.OK, response.status_code)
        data = json.loads(response.content)
        self.assertIn("error", data)
        self.assertRegex(data["error"]["message"], r"user.*Unknown user_id")

        self.test_run.refresh_from_db()
        self.assertFalse(self.test_run.cc.filter(pk=user.pk).exists())
