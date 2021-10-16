# Copyright (c) 2020-2021 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt
# pylint: disable=too-many-ancestors
from http import HTTPStatus

from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from django_tenants import utils

from tcms_tenants.tests import LoggedInTestCase
from tcms_tenants.tests import UserFactory


class TenantAdminTestCase(LoggedInTestCase):
    def tearDown(self):
        self.tester.is_superuser = False
        self.tester.save()

        super().tearDown()

    def test_cant_add_tenant_via_admin(self):
        response = self.client.get(reverse('admin:tcms_tenants_tenant_add'))
        self.assertRedirects(response,
                             reverse('admin:tcms_tenants_tenant_changelist'),
                             fetch_redirect_response=False)

    def test_cant_change_tenant_via_admin(self):
        response = self.client.get(reverse('admin:tcms_tenants_tenant_change',
                                           args=[self.tenant.pk]))
        self.assertRedirects(response,
                             reverse('admin:tcms_tenants_tenant_changelist'),
                             fetch_redirect_response=False)

    def test_cant_delete_tenant_via_admin(self):
        response = self.client.get(reverse('admin:tcms_tenants_tenant_delete',
                                           args=[self.tenant.pk]))
        self.assertRedirects(response,
                             reverse('admin:tcms_tenants_tenant_changelist'),
                             fetch_redirect_response=False)

    def test_cant_access_changelist(self):
        response = self.client.get(reverse('admin:tcms_tenants_tenant_changelist'))
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_superuser_can_access_changelist(self):
        self.tester.is_superuser = True
        self.tester.save()

        response = self.client.get(reverse('admin:tcms_tenants_tenant_changelist'))
        self.assertContains(response, 'Schema name')
        self.assertContains(response, 'Domain name')
        self.assertContains(response, self.tenant.schema_name)
        self.assertContains(response, self.tenant.domains.filter(is_primary=True).first().domain)

    def test_superuser_can_delete_tenant(self):
        self.tester.is_superuser = True
        self.tester.save()

        url = reverse('admin:tcms_tenants_tenant_delete', args=[self.tenant.pk])
        response = self.client.get(url)

        # verify there's the Yes, I'm certain button
        self.assertEqual(HTTPStatus.OK, response.status_code)
        self.assertContains(response, _("Yes, I'm sure"))

        # not simulating actual deletion b/c we don't seem to be able to switch
        # to tenant schema or to public schema witin the tests and the deletion
        # operation fails b/c current active schema is 'test'


class AuthorizedUsersAdminTestCase(LoggedInTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # reset owner for cls.tenant b/c we'd like for testing all tenants
        # to be owned by the same user
        cls.tenant.owner = cls.tester
        cls.tenant.name = 'For testing purposes'
        cls.tenant.save()

        # we give this 2nd user access to the tenant
        cls.tester2 = UserFactory()

        with utils.schema_context('public'):
            cls.tenant2 = utils.get_tenant_model()(schema_name='my_other_tenant',
                                                   owner=cls.tester)
            cls.tenant2.save()

            cls.domain2 = utils.get_tenant_domain_model()(tenant=cls.tenant2,
                                                          domain='other.example.com')
            cls.domain2.save()

    def test_can_access_changelist(self):
        response = self.client.get(reverse('admin:tcms_tenants_tenant_authorized_users_changelist'))

        self.assertContains(response, 'Username')
        self.assertContains(response, 'Full name')
        self.assertContains(response, 'Tenant name')
        self.assertContains(response, self.tester.username)
        self.assertContains(response, self.tester.get_full_name())
        self.assertContains(response, self.tenant.name)

    def test_add_displays_only_current_tenant(self):
        self.assertGreater(utils.get_tenant_model().objects.filter(owner=self.tester).count(), 1)

        response = self.client.get(reverse('admin:tcms_tenants_tenant_authorized_users_add'))

        self.assertContains(response, "<option value=''>---------</option>", html=True)
        self.assertContains(response,
                            f"<option value='{self.tenant.pk}' selected>{self.tenant}</option>",
                            html=True)
        self.assertNotContains(response, self.tenant2)

    def test_on_error_display_only_current_tenant(self):
        self.assertGreater(utils.get_tenant_model().objects.filter(owner=self.tester).count(), 1)

        response = self.client.post(
            reverse('admin:tcms_tenants_tenant_authorized_users_add'), {
                # NOTE: No tenant field specified
                'user': self.tester2.username,
                '_save': 'Save',
            })

        self.assertContains(response, "<ul class='errorlist'>", html=True)
        self.assertContains(response, "This field is required")
        self.assertContains(response, "<option value='' selected>---------</option>", html=True)
        self.assertContains(response,
                            f"<option value='{self.tenant.pk}'>{self.tenant}</option>",
                            html=True)
        self.assertNotContains(response, self.tenant2)

        self.assertContains(
            response,
            '<input id="id_user" type="text" name="user" '
            f'value="{self.tester2.username}" required>',
            html=True)

    def test_change_displays_only_current_tenant(self):
        self.assertGreater(utils.get_tenant_model().objects.filter(owner=self.tester).count(), 1)

        first_user = self.tenant.authorized_users.first()
        response = self.client.get(
            reverse('admin:tcms_tenants_tenant_authorized_users_change', args=[first_user.pk]))

        self.assertContains(response, "<option value=''>---------</option>", html=True)
        self.assertContains(response,
                            f"<option value='{self.tenant.pk}' selected>{self.tenant}</option>",
                            html=True)
        self.assertNotContains(response, self.tenant2)
