# Copyright (c) 2019 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt

from datetime import datetime, timedelta

from django.urls import reverse
from django.db import connection
from django.conf import settings
from django.http import HttpResponseRedirect

from tcms_tenants.models import *
from tcms_tenants.tests import LoggedInTestCase


class RedirectToTestCase(LoggedInTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        connection.set_schema_to_public()
        cls.tenant3 = Tenant(schema_name='tenant3', owner=cls.tester)
        cls.tenant3.save()

        cls.domain3 = Domain(tenant=cls.tenant3,
                             domain='tenant3.%s' % settings.KIWI_TENANTS_DOMAIN)
        cls.domain3.save()

    def test_redirect_to_tenant_path(self):
        expected_url = 'https://tenant3.%s/plans/search/' % settings.KIWI_TENANTS_DOMAIN
        response = self.client.get(reverse('tcms_tenants:redirect-to',
                                           args=[self.tenant3.schema_name, 'plans/search/']))

        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response['Location'], expected_url)

    def test_redirect_to_tenant_root_url(self):
        expected_url = 'https://tenant3.%s/' % settings.KIWI_TENANTS_DOMAIN
        response = self.client.get(reverse('tcms_tenants:redirect-to',
                                           args=[self.tenant3.schema_name, '']))

        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response['Location'], expected_url)


class NewTenantViewTestCase(LoggedInTestCase):
    def test_create_tenant_shows_defaults_for_trial_and_paid_until(self):
        response = self.client.get(reverse('tcms_tenants:create-tenant'))
        # assert hidden fields are shown with defaults b/c the tests below
        # can't simulate opening the page and clicking the submit button
        self.assertContains(response,
                            '<input id="id_on_trial" name="on_trial" value="True" type="hidden">',
                            html=True)
        self.assertContains(response,
                            '<input id="id_paid_until" name="paid_until" type="hidden">',
                            html=True)

    def test_create_tenant_with_name_schema_only(self):
        expected_url = 'https://tinc.%s' % settings.KIWI_TENANTS_DOMAIN
        response = self.client.post(
            reverse('tcms_tenants:create-tenant'),
            {
                'name': 'Tenant, Inc.',
                'schema_name': 'tinc',
                # this is what the default form view sends
                'on_trial': True,
                'paid_until': '',
            })

        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response['Location'], expected_url)

        tenant = Tenant.objects.get(schema_name='tinc')
        self.assertTrue(tenant.on_trial)
        self.assertIsNone(tenant.paid_until)

    def test_create_tenant_with_name_schema_on_trial_payment_date(self):
        """
            Similar invocation will be used via inherited view in
            GitHub Marketplace integration.
        """
        expected_url = 'https://subscriber.%s' % settings.KIWI_TENANTS_DOMAIN
        paid_until = datetime.now().replace(microsecond=0) + timedelta(days=30)

        response = self.client.post(
            reverse('tcms_tenants:create-tenant'),
            {
                'name': 'Subscriber LLC',
                'schema_name': 'subscriber',
                'on_trial': False,
                'paid_until': paid_until.strftime('%Y-%m-%d %H:%M:%S'),
            })

        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response['Location'], expected_url)

        tenant = Tenant.objects.get(schema_name='subscriber')
        self.assertFalse(tenant.on_trial)
        self.assertEqual(tenant.paid_until, paid_until)
