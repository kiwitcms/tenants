# Copyright (c) 2022 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

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
