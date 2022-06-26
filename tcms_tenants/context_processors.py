def tenant_navbar_processor(request):
    """
    Provide tenant name for display in navbar
    """
    tenant_name = request.tenant.schema_name
    if request.tenant.organization:
        tenant_name = request.tenant.organization
    customized_logo_contents = """
                    <li style="float:left">
                    <a>
                        <span id="tenant">
                        """ + tenant_name + """
                        </span>
                    </a>
                </li>
    """
    return customized_logo_contents
