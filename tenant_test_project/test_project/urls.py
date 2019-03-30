from django.conf.urls import include, url

from tcms.urls import urlpatterns
from tcms_tenants import urls as tcms_tenants_urls

# override default TCMS URLs and add the tenant app as well
urlpatterns += [
    url(r'^tenants/', include(tcms_tenants_urls, namespace='tenants')),
]
