# Copyright (c) 2019 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

from django import template
from django.db import connection

from tcms_tenants import utils

register = template.Library()


@register.simple_tag
def tenant_url(request, schema_name=None):
    if not schema_name:
        schema_name = connection.schema_name

    return utils.tenant_url(request, schema_name)
