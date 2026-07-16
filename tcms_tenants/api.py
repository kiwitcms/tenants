# Copyright (c) 2025-2026 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

# pylint: disable=missing-permission-required, no-self-use

from tcms.rpc.views import rpc_method
from tcms_tenants.forms import InviteUsersForm
from tcms_tenants import utils


def tenant_owner_required(request):
    """
    Authentication predicate: the user must own the current tenant.
    Returns the user if authorized, None otherwise.
    """
    if utils.owns_tenant(request.user, request.tenant):
        return request.user
    return None


@rpc_method(
    name="Tenant.invite",
    auth=tenant_owner_required,
    context_target="rpc_context",
)
def invite(
    email_addresses, notify_via_email, rpc_context=None
):  # pylint: disable=missing-api-permissions-required
    """
    .. function:: RPC Tenant.invite(email_addresses, notify_via_email)

        [Create accounts] and invite them to the current tenant!

        :param email_addresses: List of email addresses
        :type email_addresses: list(str)
        :param notify_via_email: Whether to send notification email or not
        :type notify_via_email: bool
        :param rpc_context: Provides access to the current request, protocol,
                entry point name and handler instance from the rpc method
        :type rpc_context: modernrpc.core.RpcRequestContext
        :return: List of successfully invited or errored email addresses
        :rtype: dict
        :raises PermissionDenied: if caller isn't authorized to invite other users

    .. versionadded:: 15.3
    """
    request = rpc_context.request

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
