# Copyright (c) 2022 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

# pylint: disable=import-outside-toplevel

from django.apps import AppConfig as DjangoAppConfig
from django.core.checks import register


class AppConfig(DjangoAppConfig):
    name = "tenant_groups"

    def ready(self):
        from tenant_groups import checks

        register(checks.tenant_groups_backend)
