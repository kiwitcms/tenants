# Copyright (c) 2019 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt
# pylint: disable=too-few-public-methods
from datetime import datetime, timedelta

from django.contrib import messages
from django.http import HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin
from django.utils.translation import ugettext_lazy as _

from tcms_tenants.utils import can_access


class BlockUnauthorizedUserMiddleware(MiddlewareMixin):
    """
        Raises 404 if the user making the request is not authorized
        explicitly to access the tenant instance!

        .. warning:

            This must be placed after
            ``django_tenants.middleware.main.TenantMainMiddleware`` and
            ``django.contrib.auth.middleware.AuthenticationMiddleware`` -
            usually goes at the end
    """
    # todo: rewrite this without deprecation MiddlewareMixin
    def process_request(self, request):  # pylint: disable=no-self-use
        if not can_access(request.user, request.tenant):
            return HttpResponseForbidden(_('Unauthorized'))

        return None


class BlockUnpaidTenantMiddleware:
    """
        Blocks unpaid tenants or adds warning messages if tenant is about to
        expire soon!

        .. warning:

            This must be placed after
            ``tcms_tenants.middleware.BlockUnauthorizedUserMiddleware`` -
            usually goes at the end.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.tenant.paid_util is None:
            return HttpResponseForbidden(_('Unauthorized'))

        if request.tenant.paid_util <= datetime.now():
            return HttpResponseForbidden(_('Unpaid'))

        if request.tenant.paid_util <= datetime.now() + timedelta(days=7):
            # todo: can we avoid adding message if it already exists ???
            messages.add_message(request,
                                 messages.WARNING,
                                 _('Tenant expires in less than 7 days'),
                                 fail_silently=True)

        return self.get_response(request)
