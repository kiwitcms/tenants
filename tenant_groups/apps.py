# pylint: disable=import-outside-toplevel

from django.apps import AppConfig as DjangoAppConfig
from django.core.checks import register


class AppConfig(DjangoAppConfig):
    name = "tenant_groups"

    def ready(self):
        from tenant_groups import checks

        register(checks.tenant_groups_backend)
