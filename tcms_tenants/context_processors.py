# Copyright (c) 2022 Ivajlo Karabojkov <karabojkov@kitbg.com>
# Copyright (c) 2022-2024 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

from attachments.models import Attachment
from django.template.loader import render_to_string


def tenant_navbar_processor(request):
    """
    Provide tenant name for display in navbar
    """
    if not getattr(request, "tenant", None):
        return {"CUSTOMIZED_LOGO_CONTENTS": ""}

    if request.tenant.organization:
        tenant_name = request.tenant.organization
    elif request.tenant.name:
        tenant_name = request.tenant.name
    else:
        tenant_name = request.tenant.schema_name

    tenant_logo = Attachment.objects.attachments_for_object(request.tenant).first()

    customized_logo_contents = render_to_string(
        "tcms_tenants/tenant_name.html",
        {"tenant_name": tenant_name, "tenant_logo": tenant_logo},
    )
    return {"CUSTOMIZED_LOGO_CONTENTS": customized_logo_contents}


def schema_name_processor(request):
    """
    Provide tenant.schema_name for use in templates
    """
    return {
        "TENANT_SCHEMA_NAME": getattr(
            getattr(request, "tenant", None), "schema_name", ""
        )
    }
