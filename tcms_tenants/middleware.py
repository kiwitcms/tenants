# Copyright (c) 2019 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt

from django.http import HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin
from django.utils.translation import ugettext_lazy as _

from tcms_tenants.utils import can_access


class BlockUnauthorizedUserMiddleware(MiddlewareMixin):  # pylint: disable=too-few-public-methods
    """
        Raises 404 if the user making the request is not authorized
        explicitly to access the tenant instance!

        .. warning:

            This must be places after
            ``django_tenants.middleware.main.TenantMainMiddleware`` and
            ``django.contrib.auth.middleware.AuthenticationMiddleware`` -
            usually goes at the end
    """
    # todo: rewrite this without deprecation MiddlewareMixin
    def process_request(self, request):  # pylint: disable=no-self-use
        if not can_access(request.user, request.tenant):
            return HttpResponseForbidden(_('Unauthorized'))

        return None
