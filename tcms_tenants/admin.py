# pylint: disable=no-self-use

from django.urls import reverse
from django.contrib import admin
from django.http import HttpResponseRedirect

from tcms_tenants.models import Tenant


class TenantAdmin(admin.ModelAdmin):
    actions = ['delete_selected']
    list_display = ('id', 'name', 'schema_name', 'domain_name', 'created_on', 'on_trial', 'paid_until')
    search_fields = ('name', 'schema_name')
    ordering = ['-created_on']

    def add_view(self, request, form_url='', extra_context=None):
        return HttpResponseRedirect(reverse('admin:tcms_tenants_tenant_changelist'))

    def change_view(self, request, object_id, form_url='', extra_context=None):
        return HttpResponseRedirect(reverse('admin:tcms_tenants_tenant_changelist'))

    @admin.options.csrf_protect_m
    def delete_view(self, request, object_id, extra_context=None):
        if request.user.is_superuser:
            return super().delete_view(request, object_id, extra_context)

        return HttpResponseRedirect(reverse('admin:tcms_tenants_tenant_changelist'))

    def domain_name(self, instance):
        return instance.domains.first().domain


admin.site.register(Tenant, TenantAdmin)
