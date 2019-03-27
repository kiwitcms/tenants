from django.http import Http404
from django.utils.deprecation import MiddlewareMixin


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
        # everybody can access the public schema
        if request.tenant.schema_name == 'public':
            return

        if not request.tenant.authorized_users.filter(pk=request.user.pk).exists():
            raise Http404('Tenant does not exist!')
