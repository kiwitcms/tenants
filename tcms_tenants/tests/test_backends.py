# Copyright (c) 2022 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt
# pylint: disable=too-many-ancestors
from http import HTTPStatus

from django.http import HttpResponseForbidden

from tcms_tenants.tests import LoggedInTestCase


class PubliclyReadableBackendTestCase(LoggedInTestCase):

    def test_regular_user_cant_view_list_of_all_users(self):
        self.tenant.publicly_readable = True
        self.tenant.save()

        self.assertFalse(self.tester.is_superuser)

        response = self.client.get("/admin/auth/user/")
        self.assertIsInstance(response, HttpResponseForbidden)
        self.assertEqual(HTTPStatus.FORBIDDEN, response.status_code)
