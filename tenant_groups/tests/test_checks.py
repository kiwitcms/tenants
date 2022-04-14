# Copyright (c) 2022 Alexander Todorov <atodorov@otb.bg>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt

from django.core.checks import Error
from django.test import override_settings, TestCase

from tenant_groups import checks


class CheckGroupsBackendTestCase(TestCase):
    def test_passes_when_backend_is_enabled(self):
        self.assertEqual(checks.tenant_groups_backend(None), [])

    def test_fails_when_backend_is_not_configured(self):
        with override_settings(
            AUTHENTICATION_BACKENDS=["django.contrib.auth.backends.ModelBackend"],
        ):
            expected_errors = [
                Error(
                    msg='tenant_groups.backends.GroupsBackend '
                        'is not pesent in AUTHENTICATION_BACKENDS!',
                    hint=(
                        'See '
                        'https://kiwitcms.readthedocs.io/en/latest/admin.html#tenant-permissions'
                    ),
                ),
            ]
            self.assertEqual(checks.tenant_groups_backend(None), expected_errors)
