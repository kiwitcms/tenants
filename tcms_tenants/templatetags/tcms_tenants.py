from django import template
from django.db import connection

from tcms_tenants import utils

register = template.Library()


@register.simple_tag
def tenant_url(request):
    return utils.tenant_url(request, connection.schema_name)
