# Copyright (c) 2019 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt
# pylint: disable=too-many-ancestors
from django.conf import settings
from django.http import HttpResponseForbidden

from tcms_tenants.tests import LoggedInTestCase


class BlockUnauthorizedUserMiddlewareTestCase(LoggedInTestCase):
    def test_unauthorized_user_cant_access_tenant(self):
        self.tenant.authorized_users.remove(self.tester)
        response = self.client.get('/')

        self.assertIsInstance(response, HttpResponseForbidden)
        self.assertIn('Unauthorized', str(response.content, encoding=settings.DEFAULT_CHARSET))
