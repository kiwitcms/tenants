# Copyright (c) 2022 Alexander Todorov <atodorov@otb.bg>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt

from django.conf import settings
from django.core import checks


def tenant_groups_backend(app_configs, **kwargs):  # pylint: disable=unused-argument
    errors = []
    if "tenant_groups.backends.GroupsBackend" not in settings.AUTHENTICATION_BACKENDS:
        errors.append(
            checks.Error(
                msg='tenant_groups.backends.GroupsBackend '
                    'is not pesent in AUTHENTICATION_BACKENDS!',
                hint=('See '
                      'https://kiwitcms.readthedocs.io/en/latest/admin.html#tenant-groups'),
            )
        )
    return errors
