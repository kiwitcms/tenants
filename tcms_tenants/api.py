# Copyright (c) 2025 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

# pylint: disable=missing-permission-required, no-self-use

from django.core.exceptions import PermissionDenied

from modernrpc.core import REQUEST_KEY, rpc_method
from tcms_tenants.forms import InviteUsersForm
from tcms_tenants import utils


@rpc_method(name="Tenant.invite")
def invite(
    email_addresses, notify_via_email, **kwargs
):  # pylint: disable=missing-api-permissions-required
    """
    .. function:: RPC Tenant.invite(email_addresses, notify_via_email)

        [Create accounts] and invite them to the current tenant!

        :param email_addresses: List of email addresses
        :type email_addresses: list(str)
        :param notify_via_email: Whether to send notification email or not
        :type notify_via_email: bool
        :param \\**kwargs: Dict providing access to the current request, protocol,
                entry point name and handler instance from the rpc method
        :return: List of successfully invited or errored email addresses
        :rtype: dict
        :raises PermissionDenied: if caller isn't authorized to invite other users

    .. versionadded:: 15.3
    """
    request = kwargs.get(REQUEST_KEY)

    # currently any authorized user can invite others
    if not utils.owns_tenant(request.user, request.tenant):
        raise PermissionDenied("Permission denied")

    success = []
    errored = []

    # convert input data into expected format
    for email in email_addresses:
        form = InviteUsersForm(
            {
                "email_0": email,
            }
        )
        if form.is_valid():
            utils.invite_users(request, form.cleaned_data["emails"], notify_via_email)
            success.append(email)
        else:
            errored.append(email)

    return {
        "success": success,
        "errored": errored,
    }
