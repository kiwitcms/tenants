# Copyright (c) 2019 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt


from django import forms
from django.urls import reverse
from django.contrib import admin
from django.forms.utils import ErrorList
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponseForbidden, HttpResponseRedirect

from tcms_tenants.models import Tenant
from tcms_tenants.utils import owns_tenant


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


class AuthorizedUsersChangeForm(forms.ModelForm):
    """
        A custom add/change form which will filter the available
        values of the ``tenant`` field so that only the current
        tenant is shown!
    """
    ### important notice:
    # As a security concern we would like to have this queryset set to
    # Tenant.objects.none() instead of .all(). However ModelChoiceField.to_python()
    # is trying to self.queryset.get() the currently selected value! When the queryset
    # is empty this raises ValidationError!
    # The internal mechanics of this are in BasseForm._clean_fields()::L399(Django 2.1.7)
    # which calls field.clean(value) before any clean_<field_name>() methods on the form!
    tenant = forms.models.ModelChoiceField(
        queryset=Tenant.objects.all(),  # todo: add tests to make sure we are always filtering this !!!
    )
    user = forms.models.ModelChoiceField(
        queryset=get_user_model().objects.all(),  # it is OK to be able to select between all users
    )

    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                 initial=None, error_class=ErrorList, label_suffix=None,
                 empty_permitted=False, instance=None, use_required_attribute=None,
                 renderer=None):
        super().__init__(data, files, auto_id, prefix,
                         initial, error_class, label_suffix,
                         empty_permitted, instance, use_required_attribute,
                         renderer)
        # this is passed by ModelAdmin._chageform_view():L1578
        # when adding a new object
        if initial and 'tenant' in initial:
            self.fields['tenant'].queryset = Tenant.objects.filter(pk=initial['tenant'])
        # this is passed by ModelAdmin._chageform_view():L1581
        # when changing an existing object
        elif instance:
            self.fields['tenant'].queryset = Tenant.objects.filter(pk=instance.tenant.pk)


class AuthorizedUsersAdmin(admin.ModelAdmin):
    """
        Allows administering which users are authorized for tenants!
    """
    actions = ['delete_selected']
    list_display = ('user_username', 'user_full_name', 'tenant_name')
    search_fields = ('user__username', 'tenant__name')

    form = AuthorizedUsersChangeForm

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
            Show only users authorized for the current tenant!
        """
        return super().get_queryset(request).filter(tenant=request.tenant)

    def get_changeform_initial_data(self, request):
        """
            Pass the current tenant to AuthorizedUsersChangeForm.__init__()
            which will filter the available tenants and only show the current
            one when add/change objects!
        """
        return {'tenant': request.tenant.pk}

    def has_add_permission(self, request, obj=None):
        """
            Allow to add new authorized users.
        """
        return owns_tenant(request.user, request.tenant)

    def has_change_permission(self, request, obj=None):
        """
            Allow to display the list of of authorized users.
        """
        return owns_tenant(request.user, request.tenant)

    def has_delete_permission(self, request, obj=None):
        """
            Allow to delete selected users.
        """
        return request.user.is_superuser or owns_tenant(request.user, request.tenant)

    def has_module_permission(self, request):
        """
            Allow this module to be seen in main admin page.
        """
        return owns_tenant(request.user, request.tenant)

    def get_model_perms(self, request):
        """
            Allow this module to be seen in main admin page.
        """
        if request.user.is_superuser:
            return super().get_model_perms(request)

        return {'view': owns_tenant(request.user, request.tenant)}


admin.site.register(Tenant, TenantAdmin)
admin.site.register(Tenant.authorized_users.through, AuthorizedUsersAdmin)
