# Copyright (c) 2022-2023 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

import datetime

from django.contrib.auth import get_user_model

from tcms_tenants.forms import NewTenantForm
from tcms_tenants.utils import create_tenant


def create_oss_tenant(owner, name, schema_name, organization):
    """
    Used to create tenants for our OSS program. Executed by the
    instance administrator!
    """

    class FakeRequest:  # pylint: disable=too-few-public-methods,nested-class-found
        is_secure = True
        user = None

        def __init__(self, username):
            self.user = get_user_model().objects.get(username=username)

    request = FakeRequest(owner)

    form = NewTenantForm(
        {
            "owner": request.user.pk,
            "name": name,
            "schema_name": schema_name.lower(),
            "organization": organization,
            "publicly_readable": False,
            "paid_until": datetime.datetime(2999, 12, 31),
        }
    )
    if form.is_valid():
        return create_tenant(form, request)

    raise RuntimeError(list(form.errors.items()))
