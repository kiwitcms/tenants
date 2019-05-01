# Copyright (c) 2019 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt

from django.urls import reverse
from django.db import connection
from django.conf import settings
from django.http import HttpResponseRedirect

from tcms_tenants.models import *
from tcms_tenants.tests import LoggedInTestCase


class RedirectToTestCase(LoggedInTestCase):
    @classmethod
    def setUpClass(cls):
        connection.set_schema_to_public()
        cls.tenant3 = Tenant(schema_name='tenant3')
        cls.tenant3.save()

        cls.domain3 = Domain(tenant=cls.tenant3,
                             domain='tenant3.%s' % settings.KIWI_TENANTS_DOMAIN)
        cls.domain3.save()

        super().setUpClass()

    def test_redirect_to_tenant_path(self):
        expected_url = 'https://tenant3.%s/plans/search/' % settings.KIWI_TENANTS_DOMAIN
        response = self.client.get(reverse('tcms_tenants:redirect-to',
                                           args=[self.tenant3.schema_name, 'plans/search']))

        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response['Location'], expected_url)
