# Copyright (c) 2019-2020 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt

from django.urls import re_path
from tcms_tenants import views

app_name = 'tcms_tenants'

urlpatterns = [
    re_path(r'^create/$', views.NewTenantView.as_view(), name='create-tenant'),
    re_path(r'^invite/$', views.InviteUsers.as_view(), name='invite-users'),
    re_path(r'^go/to/(?P<tenant>\w+)/(?P<path>.*)$',
            views.RedirectTo.as_view(), name='redirect-to'),
]
