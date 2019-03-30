# Copyright (c) 2019 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt

from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.views.generic.base import TemplateView
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required

from tcms_tenants import utils
from tcms_tenants.forms import NewTenantForm

@method_decorator(login_required, name='dispatch')
class NewTenantView(TemplateView):
    """
        Everybody is allowed to create new tenants.
        Depending on additional configuration they may have to pay
        for using them!
    """
    template_name = 'tcms_tenants/new.html'

    def get(self, request, *args, **kwargs):
        context_data = {
            'form': NewTenantForm(),
            'tcms_tenants_domain': settings.TCMS_TENANTS_DOMAIN,
        }

        return render(request, self.template_name, context_data)

    def post(self, request, *args, **kwargs):
        form = NewTenantForm(request.POST)
        if form.is_valid():
            tenant = utils.create_tenant(form.cleaned_data['name'],
                                         form.cleaned_data['schema_name'],
                                         request.user)
            # all is successfull so redirect to the new tenant
            return HttpResponseRedirect(utils.tenant_url(request, tenant.schema_name))

        context_data = {
            'form': form,
            'tcms_tenants_domain': settings.TCMS_TENANTS_DOMAIN,
        }
        return render(request, self.template_name, context_data)
