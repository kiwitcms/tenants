# Copyright (c) 2021 Ivajlo Karabojkov <karabojkov@kitbg.com>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

import os

from django.core import checks


def tenants_env_check(app_configs, **kwargs):  # pylint: disable=unused-argument
    errors = []
    if not os.environ.get("KIWI_TENANTS_DOMAIN"):
        errors.append(
            checks.Error(
                msg="KIWI_TENANTS_DOMAIN environment variable is not set!",
                hint=(
                    "This variable is mandatory, "
                    "see https://github.com/kiwitcms/tenants#installation"
                ),
            )
        )
    return errors
