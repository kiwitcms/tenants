# Copyright (c) 2020 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt
# pylint: disable=too-many-ancestors
from http import HTTPStatus

from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from tcms_tenants.tests import LoggedInTestCase


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
