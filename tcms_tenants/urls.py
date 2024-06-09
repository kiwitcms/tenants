# Copyright (c) 2019-2021 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

from django.urls import re_path
from tcms_tenants import views

app_name = "tcms_tenants"

urlpatterns = [
    re_path(r"^create/$", views.NewTenantView.as_view(), name="create-tenant"),
    re_path(r"^edit/$", views.UpdateTenantView.as_view(), name="edit-tenant"),
    re_path(r"^invite/$", views.InviteUsers.as_view(), name="invite-users"),
    re_path(
        r"^go/to/(?P<tenant>\w+)/(?P<path>.*)$",
        views.RedirectTo.as_view(),
        name="redirect-to",
    ),
]
