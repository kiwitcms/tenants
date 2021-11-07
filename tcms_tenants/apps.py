# pylint: disable=import-outside-toplevel
from django.apps import AppConfig as DjangoAppConfig
from django.core.checks import register


class AppConfig(DjangoAppConfig):
    name = "tcms_tenants"

    def ready(self):
        from tcms_tenants import checks

        register(checks.tenants_env_check)
