# Copyright (c) 2022 Alexander Todorov <atodorov@otb.bg>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt

from django_tenants.utils import get_public_schema_name, get_tenant_model, tenant_context
from tcms.core.management.commands import refresh_permissions

from tenant_groups.models import Group as TenantGroup


class Command(refresh_permissions.Command):
    help = "Refresh permissions for tenant groups 'Admin' & 'Tester'."

    group_model = TenantGroup
    admin_permissions_filter = {
        'content_type__app_label__in': TenantGroup.relevant_apps,
    }
    tester_permissions_filter = {
        'content_type__app_label__in': TenantGroup.relevant_apps,
    }

    def handle(self, *args, **kwargs):
        for tenant in get_tenant_model().objects.exclude(
            schema_name=get_public_schema_name(),
        ):
            output = None
            if kwargs["verbosity"]:
                output = self.stdout

            with tenant_context(tenant):
                if output:
                    output.write(
                        f"\n\n === Refreshing permissions for tenant '{tenant.schema_name}' ===")

                self.execute_commands(*args, **kwargs)

                if output:
                    output.write(
                        f"\n\n === End refreshing permissions for tenant '{tenant.schema_name}' ==="
                    )
