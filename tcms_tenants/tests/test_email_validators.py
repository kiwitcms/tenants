# Copyright (c) 2025 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

# pylint: disable=too-many-ancestors

from django.test import override_settings
from django_tenants.utils import tenant_context
from mock import patch

from tcms.tests.factories import TestCaseFactory
from tcms_tenants.email_validators import blacklist_non_authorized
from tcms_tenants.tests import LoggedInTestCase, UserFactory


class EmailValidatorsTestCase(LoggedInTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.regular_user = UserFactory()
        cls.regular_user.set_password("password")
        cls.regular_user.save()

        with tenant_context(cls.tenant):
            cls.test_case = TestCaseFactory(
                author=cls.tenant.owner, default_tester=cls.tester
            )
            cls.test_case.emailing.notify_on_case_update = True
            cls.test_case.emailing.auto_to_case_author = True
            cls.test_case.emailing.auto_to_case_tester = True
            cls.test_case.emailing.add_cc([cls.regular_user.email])

    def test_unauthorized_user_does_not_receive_email(self):
        with override_settings(
            EMAIL_VALIDATORS=(blacklist_non_authorized,),
        ), patch("tcms.core.utils.mailto.send_mail") as send_mail:
            with tenant_context(self.tenant):
                self.test_case.summary = "updated via tests"
                self.test_case.save()

            send_mail.assert_called_once()
            self.assertIn(self.tenant.owner.email, send_mail.call_args_list[0][0][-1])
            self.assertIn(self.tester.email, send_mail.call_args_list[0][0][-1])

            # CC was excluded b/c address isn't authorized for this tenant
            self.assertNotIn(
                self.regular_user.email, send_mail.call_args_list[0][0][-1]
            )
