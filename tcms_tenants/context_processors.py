from django.template.loader import render_to_string  # noqa: E402


def tenant_navbar_processor(request):
    """
    Provide tenant name for display in navbar
    """
    tenant_name = request.tenant.schema_name
    if request.tenant.organization:
        tenant_name = request.tenant.organization
    if request.tenant.name:
        tenant_name = request.tenant.name
    customized_logo_contents = render_to_string(
        "tcms_tenants/tenant_name.html", {"tenant_name": tenant_name}
    )
    return {"CUSTOMIZED_LOGO_CONTENTS": customized_logo_contents}
