# Copyright (c) 2019 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt

from django.http import Http404
from django.utils.deprecation import MiddlewareMixin

from tcms_tenants.perms import can_access


class BlockUnauthorizedUserMiddleware(MiddlewareMixin):
    """
        Raises 404 if the user making the request is not authorized
        explicitly to access the tenant instance!

        .. warning:

            This must be places after
            ``django_tenants.middleware.main.TenantMainMiddleware`` and
            ``django.contrib.auth.middleware.AuthenticationMiddleware`` -
            usually goes at the end
    """
    def process_request(self, request):
        if not can_access(request.user, request.tenant):
            raise Http404('Tenant does not exist!')
