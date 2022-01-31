# Copyright (c) 2022 Alexander Todorov <atodorov@MrSenko.com>

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Permission

from django_tenants.utils import get_public_schema_name, tenant_context
from tcms_tenants.utils import get_current_tenant


class GroupsBackend(ModelBackend):
    """
    Backend which returns group permissions configured per-tenant but keeps
    individual user permissions!

    NOTE: Individually assigned permissions have higher priority
    (are valid across tenants) compared to group permissions.
    """
    public_schema_name = get_public_schema_name()

    @property
    def tenant(self):
        return get_current_tenant()

    def get_group_permissions(self, user_obj, obj=None):
        # group permissions configured on public tenant via
        # django.contrib.auth.models.Group
        if self.tenant.schema_name == self.public_schema_name:
            return super().get_group_permissions(user_obj, obj)

        # permissions configured per-tenant via
        # tenant_groups.models.Group
        with tenant_context(self.tenant):
            permissions = Permission.objects.filter(
                tenant_groups__user_set__in=[user_obj]
            ).values_list(
                'content_type__app_label',
                'codename'
            ).order_by()

            return {f"{ct}.{name}" for ct, name in permissions}
