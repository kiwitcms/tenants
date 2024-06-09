# Copyright (c) 2020-2022 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _


# Follows the format of ``tcms.settings.common.MENU_ITEMS``
MENU_ITEMS = [
    (
        _("Tenant"),
        [
            (_("Create"), reverse_lazy("tcms_tenants:create-tenant")),
            (_("Edit"), reverse_lazy("tcms_tenants:edit-tenant")),
            ("-", "-"),
            (_("Groups"), "/admin/tenant_groups/group/"),
            ("-", "-"),
            (_("Invite users"), reverse_lazy("tcms_tenants:invite-users")),
            (_("Authorized users"), "/admin/tcms_tenants/tenant_authorized_users/"),
        ],
    ),
]
