# Copyright (c) 2021 Ivajlo Karabojkov <karabojkov@kitbg.com>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

# pylint: disable=import-outside-toplevel
from django.apps import AppConfig as DjangoAppConfig
from django.core.checks import register


class AppConfig(DjangoAppConfig):
    name = "tcms_tenants"

    def ready(self):
        from tcms_tenants import checks

        register(checks.tenants_env_check)
