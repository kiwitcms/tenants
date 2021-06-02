# Copyright (c) 2021 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt
# pylint: disable=too-many-ancestors

from django.urls import reverse
from django.http import HttpResponseForbidden

from tcms_tenants.tests import LoggedInTestCase


class PubliclyReadableTestCase(LoggedInTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # self.tester is not authorized
        cls.tenant.authorized_users.remove(cls.tester)

        # but the tenant is publicly readable
        cls.tenant.publicly_readable = True
        cls.tenant.save()

    @classmethod
    def tearDownClass(cls):
        cls.tenant.publicly_readable = False
        cls.tenant.save()

    def test_unauthorized_user_can_view_on_publicly_readable_tenant(self):
        response = self.client.get(
            reverse('test_plan_url_short', args=[self.test_plan_by_owner.pk]),
            follow=True,
        )

        self.assertContains(response, self.test_plan_by_owner.name)
        self.assertContains(response, "TP-%d" % self.test_plan_by_owner.pk)
        self.assertContains(response, self.test_plan_by_owner.text)

    def test_unauthorized_user_cannot_edit_on_publicly_readable_tenant(self):
        target_url = reverse('plan-edit', args=[self.test_plan_by_owner.pk])
        response = self.client.get(target_url)
        self.assertRedirects(response, reverse("tcms-login") + "?next=" + target_url)

    def test_unauthorized_user_cannot_delete_on_publicly_readable_tenant(self):
        response = self.client.get(
            reverse('admin:testplans_testplan_delete', args=[self.test_plan_by_owner.pk]),
        )
        self.assertIsInstance(response, HttpResponseForbidden)
