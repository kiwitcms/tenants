# Copyright (c) 2019-2024 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

from django_tenants.utils import (
    get_public_schema_name,
    schema_context,
    tenant_context,
)


def user_deactivated(sender, **kwargs):  # pylint: disable=unused-argument
    """
    Remove a deactivated user account from all authorized tenants
    and from all tenant groups on each tenant!

    .. warning::

        This handler is connected to the ``USER_DEACTIVATED_SIGNAL`` by default!
    """
    if kwargs.get("raw", False):
        return

    user = kwargs.get("user")
    if not user:
        return

    tenant_set = []
    with schema_context(get_public_schema_name()):
        tenant_set = list(user.tenant_set.all())

    for tenant in tenant_set:
        with tenant_context(tenant):
            # clear all tenant groups
            user.tenant_groups.clear()

            # clear permissions assigned on this tenant
            user.user_permissions.clear()

    # remove user from all tenants they've been authorized previously
    with schema_context(get_public_schema_name()):
        user.tenant_set.clear()
