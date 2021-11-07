import os
from unittest.mock import patch

from django.core.checks import Error

from tcms_tenants import checks
from tcms_tenants.tests import LoggedInTestCase


class SystemCheckTestCase(LoggedInTestCase):
    def test_check_passes_when_env_var_is_set(self):
        with patch.dict(os.environ, {
            'KIWI_TENANTS_DOMAIN': 'test.com',
        }, True):
            self.assertEqual(checks.tenants_env_check(None), [])

    def test_check_fails_when_env_var_is_not_set(self):
        expected_errors = [
            Error(
                msg='KIWI_TENANTS_DOMAIN environment variable is not set!',
                hint=('This variable is mandatory, '
                      'see https://github.com/kiwitcms/tenants#installation'),
            ),
        ]
        with patch.dict(os.environ, {
            'KIWI_TENANTS_DOMAIN': '',
        }, True):
            self.assertEqual(checks.tenants_env_check(None), expected_errors)
