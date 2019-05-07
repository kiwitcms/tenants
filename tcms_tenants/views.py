# Copyright (c) 2019 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt

from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.template.loader import select_template
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
    def get_template_names(self):
        """
            Allow downstream installations to override the template. For example
            to provide a link to SLA or hosting policy! The overriden template
            can extend the base one if needed.
        """
        return ['tcms_tenants/override_new.html', 'tcms_tenants/new.html']

    def get_context_data(self, **kwargs):
        return {
            'form': NewTenantForm(),
            'tcms_tenants_domain': settings.KIWI_TENANTS_DOMAIN,
        }

    def post(self, request, *args, **kwargs):
        form = NewTenantForm(request.POST)
        if form.is_valid():
            tenant = utils.create_tenant(form.cleaned_data, request)
            # all is successfull so redirect to the new tenant
            return HttpResponseRedirect(utils.tenant_url(request, tenant.schema_name))

        context_data = {
            'form': form,
            'tcms_tenants_domain': settings.KIWI_TENANTS_DOMAIN,
        }
        # gets the first template which exists
        template_name = select_template(self.get_template_names()).template.name
        return render(request, template_name, context_data)


@login_required
def redirect_to(request, tenant, path):
    """
        Will redirect to tenant.domain.domain/path!

        Used together with GitHub logins and the ``tenant_url``
        template tag!

        When trying to do GitHub login on a tenant sub-domain
        the HTML href will actually point to

        https://public.tenants.localdomain/login/github?next=/tenants/go/to/tenant/path

        instead of

        http://tenant.tenants.localdomain/login/github?next=path

        This is to prevent redirect_uri mismatch errors!
    """
    target_url = '%s/%s' % (utils.tenant_url(request, tenant), path)
    return HttpResponseRedirect(target_url)
