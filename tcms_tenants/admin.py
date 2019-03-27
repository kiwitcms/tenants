# pylint: disable=no-self-use

from django.urls import reverse
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponseForbidden, HttpResponseRedirect

from tcms_tenants.models import Tenant


class TenantAdmin(admin.ModelAdmin):
    """
        Allows only super-user to see and delete tenants!
    """
    actions = ['delete_selected']
    list_display = ('id', 'name', 'schema_name', 'domain_name', 'created_on', 'on_trial', 'paid_until')
    search_fields = ('name', 'schema_name')
    ordering = ['-created_on']

    def add_view(self, request, form_url='', extra_context=None):
        return HttpResponseRedirect(reverse('admin:tcms_tenants_tenant_changelist'))

    def change_view(self, request, object_id, form_url='', extra_context=None):
        return HttpResponseRedirect(reverse('admin:tcms_tenants_tenant_changelist'))

    @admin.options.csrf_protect_m
    def changelist_view(self, request, extra_context=None):
        if request.user.is_superuser:
            return super().changelist_view(request, extra_context)

        return HttpResponseForbidden(_('Unauthorized'))

    @admin.options.csrf_protect_m
    def delete_view(self, request, object_id, extra_context=None):
        if request.user.is_superuser:
            return super().delete_view(request, object_id, extra_context)

        return HttpResponseRedirect(reverse('admin:tcms_tenants_tenant_changelist'))

    def domain_name(self, instance):
        return instance.domains.first().domain


class AuthorizedUsersAdmin(admin.ModelAdmin):
    """
        Allows administering which users are authorized for tenants!
    """
    list_display = ('user_username', 'user_full_name', 'tenant_name')
    search_fields = ('user__username', 'tenant__name')

    def user_username(self, instance):
        return instance.user.username
    user_username.short_description = _('Username')
    user_username.admin_order_field = 'user__username'

    def user_full_name(self, instance):
        return instance.user.get_full_name()
    user_full_name.short_description = _('Full name')

    def tenant_name(self, instance):
        return instance.tenant.name
    tenant_name.admin_order_field = 'tenant__name'

    def get_queryset(self, request):
        """
            When viewing as non-super-user it will show the users only
            for your tenant!
        """
        qs = super().get_queryset(request)

        if not request.user.is_superuser:
            qs = qs.filter(tenant=request.tenant)

        return qs


admin.site.register(Tenant, TenantAdmin)
admin.site.register(Tenant.authorized_users.through, AuthorizedUsersAdmin)
