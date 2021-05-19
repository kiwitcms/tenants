# Copyright (c) 2021 Alexander Todorov <atodorov@MrSenko.com>

from django.contrib.auth.backends import BaseBackend

from tcms_tenants.utils import get_current_tenant


class PubliclyReadableBackend(BaseBackend):
    """
    Backend which always returns True for *.view_* permissions for
    publicly readable tenants!
    """

    def has_perm(self, user_obj, perm, obj=None):
        current_tenant = get_current_tenant()

        # allow everyone to view
        if current_tenant.publicly_readable and perm.find(".view_") > -1:
            return True

        return super().has_perm(user_obj, perm, obj=obj)
