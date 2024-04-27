# Copyright (c) 2019-2024 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt
# pylint: disable=too-many-ancestors
from datetime import timedelta
from mock import patch

from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.http import HttpResponseRedirect
from django.test import override_settings
from django.utils.translation import gettext_lazy as _

from django_tenants.utils import tenant_context

from tcms.tests import deny_certain_email_addresses

from tcms_tenants.models import Tenant
from tcms_tenants.forms import VALIDATION_RE
from tcms_tenants.tests import LoggedInTestCase, TenantGroupsTestCase
from tcms_tenants.oss_utils import create_oss_tenant

from tenant_groups.models import Group as TenantGroup


UserModel = get_user_model()


class RedirectToTestCase(LoggedInTestCase):
    def test_redirect_to_tenant_path(self):
        # note: see LoggedInTestCase.get_test_tenant_domain()
        expected_url = "https://tenant.fast-test.com/plans/search/"
        response = self.client.get(
            reverse(
                "tcms_tenants:redirect-to",
                args=[self.tenant.schema_name, "plans/search/"],
            )
        )

        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response["Location"], expected_url)

    def test_redirect_to_tenant_root_url(self):
        # note: see LoggedInTestCase.get_test_tenant_domain()
        expected_url = "https://tenant.fast-test.com/"
        response = self.client.get(
            reverse("tcms_tenants:redirect-to", args=[self.tenant.schema_name, ""])
        )

        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response["Location"], expected_url)


class NewTenantViewTestCase(TenantGroupsTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        add_tenant = Permission.objects.get(
            content_type__app_label="tcms_tenants", codename="add_tenant"
        )
        cls.tester.user_permissions.add(add_tenant)

    def test_create_tenant_shows_defaults_for_trial_and_paid_until(self):
        response = self.client.get(reverse("tcms_tenants:create-tenant"))
        self.assertContains(response, _("New tenant"))
        # assert hidden fields are shown with defaults b/c the tests below
        # can't simulate opening the page and clicking the submit button
        self.assertContains(
            response,
            'class="bootstrap-switch" name="publicly_readable" type="checkbox"',
        )
        self.assertContains(
            response,
            '<input id="id_paid_until" name="paid_until" type="hidden">',
            html=True,
        )
        self.assertContains(response, f"Validation pattern: {VALIDATION_RE.pattern}")

    def test_invalid_schema_name_shows_errors(self):
        response = self.client.post(
            reverse("tcms_tenants:create-tenant"),
            {
                "name": "Dash Is Not Allowed",
                "schema_name": "kiwi-tcms",
                "publicly_readable": False,
                "paid_until": "",
            },
        )

        self.assertContains(response, "Invalid string")
        self.assertContains(response, f"Validation pattern: {VALIDATION_RE.pattern}")
        self.assertFalse(Tenant.objects.filter(schema_name="kiwi-tcms").exists())

    def test_invalid_domain_name_shows_errors(self):
        response = self.client.post(
            reverse("tcms_tenants:create-tenant"),
            {
                "name": "Underscore is allowed in Postres but not in domains",
                "schema_name": "kiwi_tcms",
                "publicly_readable": False,
                "paid_until": "",
            },
        )

        self.assertContains(response, "Invalid string")
        self.assertContains(response, f"Validation pattern: {VALIDATION_RE.pattern}")
        self.assertFalse(Tenant.objects.filter(schema_name="kiwi_tcms").exists())

    def test_existing_schema_name_is_invalid(self):
        response = self.client.post(
            reverse("tcms_tenants:create-tenant"),
            {
                "name": "Use an existing schema name",
                "schema_name": self.tenant.schema_name,
                "publicly_readable": False,
                "paid_until": "",
            },
        )

        self.assertContains(response, "Schema name already in use")
        self.assertContains(response, f"Validation pattern: {VALIDATION_RE.pattern}")

    @patch("tcms.core.utils.mailto.send_mail")
    def test_create_tenant_with_name_schema_only(self, send_mail):
        expected_url = f"https://tinc.{settings.KIWI_TENANTS_DOMAIN}"
        response = self.client.post(
            reverse("tcms_tenants:create-tenant"),
            {
                "name": "Tenant, Inc.",
                "schema_name": "tinc",
                # this is what the default form view sends
                "owner": self.tester.pk,
                "publicly_readable": False,
                "paid_until": "",
            },
        )

        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response["Location"], expected_url)

        # assert tenant was created
        tenant = Tenant.objects.get(schema_name="tinc")
        self.assertFalse(tenant.publicly_readable)
        self.assertIsNone(tenant.paid_until)

        # assert email was sent
        self.assertTrue(send_mail.called)
        self.assertEqual(send_mail.call_count, 1)

    def test_create_tenant_with_name_schema_publicly_readable_payment_date(self):
        """
        Similar invocation will be used via inherited view in
        GitHub Marketplace integration.
        """
        tenant = Tenant.objects.filter(schema_name="subscriber").first()
        self.assertIsNone(tenant)

        expected_url = f"https://subscriber.{settings.KIWI_TENANTS_DOMAIN}"
        paid_until = timezone.now().replace(microsecond=0) + timedelta(days=30)

        response = self.client.post(
            reverse("tcms_tenants:create-tenant"),
            {
                "name": "Subscriber LLC",
                "schema_name": "subscriber",
                "publicly_readable": False,
                "paid_until": paid_until.strftime("%Y-%m-%d %H:%M:%S"),
                # this is what the default form view sends
                "owner": self.tester.pk,
            },
        )

        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response["Location"], expected_url)

        tenant = Tenant.objects.get(schema_name="subscriber")
        self.assertFalse(tenant.publicly_readable)
        self.assertEqual(tenant.paid_until, paid_until)

        # assert tenant owner was added to default groups
        with tenant_context(tenant):
            self.assertTrue(
                tenant.owner.tenant_groups.filter(name="Administrator").exists()
            )
            self.assertTrue(tenant.owner.tenant_groups.filter(name="Tester").exists())

    @patch("tcms.core.utils.mailto.send_mail")
    def test_create_oss_tenant_with_helper_function(self, send_mail):
        tenant = create_oss_tenant(
            self.tester.username, "osstenant", "osstenant", "Free Organization"
        )

        # assert tenant owner was added to default groups
        with tenant_context(tenant):
            self.assertTrue(
                tenant.owner.tenant_groups.filter(name="Administrator").exists()
            )
            self.assertTrue(tenant.owner.tenant_groups.filter(name="Tester").exists())

        # assert tenant was created
        self.assertFalse(tenant.publicly_readable)
        self.assertEqual(tenant.owner.pk, self.tester.pk)
        # OSS tenants are valid until year 2999
        self.assertGreater(tenant.paid_until - timezone.now(), timedelta(days=1000))

        # assert email was sent
        self.assertTrue(send_mail.called)
        self.assertEqual(send_mail.call_count, 1)


class InviteUsersViewTestCase(TenantGroupsTestCase):
    @override_settings(DEFAULT_GROUPS=["InvitedUsers"])
    @patch("tcms.core.utils.mailto.send_mail")
    def test_invited_users_are_granted_access(self, send_mail):
        with tenant_context(self.tenant):
            TenantGroup.objects.create(name="InvitedUsers")

        self.assertFalse(
            UserModel.objects.filter(username="invited-via-email").exists()
        )

        response = self.client.post(
            reverse("tcms_tenants:invite-users"),
            {
                "email_0": "invited-via-email@example.com",
            },
        )

        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response["Location"], "/")

        self.assertTrue(send_mail.called)
        self.assertEqual(send_mail.call_count, 1)

        invited_user = UserModel.objects.get(username="invited-via-email")
        self.assertTrue(invited_user.is_active)
        self.assertTrue(
            self.tenant.authorized_users.filter(pk=invited_user.pk).exists()
        )

        self.assertTrue(invited_user.tenant_groups.filter(name="InvitedUsers").exists())
        self.assertFalse(invited_user.tenant_groups.filter(name="Tester").exists())

    @override_settings(
        EMAIL_VALIDATORS=(deny_certain_email_addresses,),
    )
    @patch("tcms.core.utils.mailto.send_mail")
    def test_no_invites_sent_when_form_validation_fails(self, send_mail):
        invitation_data = {
            "email_0": "via-email@example.com",
            "email_1": "invalid@yahoo.com",
            "email_2": "tester-555@example.bg",
        }

        for address in invitation_data.values():
            self.assertFalse(UserModel.objects.filter(username=address).exists())

        response = self.client.post(
            reverse("tcms_tenants:invite-users"),
            {
                "email_0": "via-email@example.com",
                "email_1": "invalid@yahoo.com",
                "email_2": "tester-555@example.bg",
            },
        )

        send_mail.assert_not_called()
        self.assertNotIsInstance(response, HttpResponseRedirect)
        self.assertContains(response, "@yahoo email address has been denied")

        for address in invitation_data.values():
            self.assertContains(response, address)
            self.assertFalse(UserModel.objects.filter(username=address).exists())


class UpdateTenantViewTestCase(LoggedInTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.change_tenant = Permission.objects.get(
            content_type__app_label="tcms_tenants", codename="change_tenant"
        )
        cls.tester.user_permissions.add(cls.change_tenant)

        # name required for edit operations below
        cls.tenant.name = "Fast Inc."
        cls.tenant.save()

    def tearDown(self):
        self.client.logout()

        self.tenant.publicly_readable = False
        self.tenant.save()

        self.tester.is_superuser = False
        self.tester.save()
        super().tearDown()

    def update_and_assert_tenant(self):
        response = self.client.post(
            reverse("tcms_tenants:edit-tenant"),
            {
                "name": self.tenant.name,
                "schema_name": self.tenant.schema_name,
                "publicly_readable": True,
                "paid_until": "",
            },
            follow=True,
        )

        # Then
        self.assertRedirects(response, "/")

        self.tenant.refresh_from_db()
        self.assertTrue(self.tenant.publicly_readable)

    def test_super_user_can_edit_any_tenant(self):
        # Given
        self.tester.is_superuser = True
        self.tester.save()
        self.assertNotEqual(self.tester, self.tenant.owner)
        self.assertFalse(self.tenant.publicly_readable)

        # When
        response = self.client.get(reverse("tcms_tenants:edit-tenant"))

        # Then
        self.assertContains(response, _("Edit tenant"))
        self.update_and_assert_tenant()

    def test_owner_can_edit_own_tenant(self):
        # Given
        self.tenant.owner.set_password("password")
        self.tenant.owner.save()
        self.tenant.owner.user_permissions.add(self.change_tenant)
        self.assertFalse(self.tenant.publicly_readable)

        self.client.logout()
        self.client.login(username=self.tenant.owner.username, password="password")
        self.assertFalse(self.tenant.publicly_readable)

        # When
        response = self.client.get(reverse("tcms_tenants:edit-tenant"))

        # Then
        self.assertContains(response, _("Edit tenant"))
        self.update_and_assert_tenant()

    def test_non_owner_cant_edit_tenant(self):
        # Given
        self.assertNotEqual(self.tester, self.tenant.owner)
        self.assertFalse(self.tester.is_superuser)
        self.assertFalse(self.tenant.publicly_readable)

        # When: get
        response = self.client.get(reverse("tcms_tenants:edit-tenant"), follow=True)

        # Then
        self.assertContains(
            response,
            _("Only super-user and tenant owner are allowed to edit tenant properties"),
        )
        self.assertRedirects(response, "/")

        # When: post
        response = self.client.post(
            reverse("tcms_tenants:edit-tenant"),
            {
                "name": self.tenant.name,
                "schema_name": self.tenant.schema_name,
                "publicly_readable": True,
                "paid_until": "",
            },
            follow=True,
        )

        # Then
        self.assertContains(
            response,
            _("Only super-user and tenant owner are allowed to edit tenant properties"),
        )
        self.assertRedirects(response, "/")

        self.tenant.refresh_from_db()
        self.assertFalse(self.tenant.publicly_readable)
