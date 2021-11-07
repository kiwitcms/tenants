# Copyright (c) 2021-2022 Ivajlo Karabojkov <karabojkov@kit.bg>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt


import os

from django.core import checks


def tenants_env_check(app_configs, **kwargs):  # pylint: disable=unused-argument
    errors = []
    if not os.environ.get('KIWI_TENANTS_DOMAIN'):
        errors.append(
            checks.Error(
                msg='KIWI_TENANTS_DOMAIN environment variable is not set!',
                hint=('This variable is mandatory, '
                      'see https://github.com/kiwitcms/tenants#installation'),
            )
        )
    return errors
