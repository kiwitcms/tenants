def can_access(user, tenant):
    # everybody can access the public schema
    if tenant.schema_name == 'public':
        return True

    return tenant.authorized_users.filter(pk=user.pk).exists()


def owns_tenant(user, tenant):
    return tenant.schema_name != 'public' and \
            tenant.authorized_users.filter(pk=user.pk).exists()
