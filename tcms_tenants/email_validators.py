# pylint: disable=import-outside-toplevel

#
# Copyright (c) 2025 Alexander Todorov <atodorov@otb.bg>
# Licensed under the GPL-3.0: https://www.gnu.org/licenses/gpl-3.0.txt
#


def blacklist_non_authorized(email):
    """
    Do not send emails to addresses which aren't authorized on the current
    tenant! e.g. added by accident via CC.
    """
    from django.forms import ValidationError
    from tcms_tenants.utils import get_current_tenant

    tenant = get_current_tenant()

    if not tenant.authorized_users.filter(email__iexact=email).exists():
        raise ValidationError(
            f"{email} is not authorized on tenant {tenant.schema_name}"
        )
