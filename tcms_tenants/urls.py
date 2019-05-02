# Copyright (c) 2019 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt

from django.conf.urls import url
from tcms_tenants import views

app_name = 'tcms_tenants'

urlpatterns = [
    url(r'^create/$', views.NewTenantView.as_view(), name='create-tenant'),
    url(r'^go/to/(?P<tenant>\w+)/(?P<path>.*)$', views.redirect_to, name='redirect-to'),
]
