# Copyright (c) 2020 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _


# Follows the format of ``tcms.settings.common.MENU_ITEMS``
MENU_ITEMS = [
    (_('Tenant'), [
        (_('Create'), reverse_lazy('tcms_tenants:create-tenant')),
        ('-', '-'),
        (_('Invite users'), reverse_lazy('tcms_tenants:invite-users')),
        (_('Authorized users'), '/admin/tcms_tenants/tenant_authorized_users/'),
    ]),
]
