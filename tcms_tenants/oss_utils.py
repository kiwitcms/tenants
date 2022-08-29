# Copyright (c) 2019-2022 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt

import datetime

from django.contrib.auth import get_user_model
from tcms.core.utils import form_errors_to_list

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

    form = NewTenantForm({
        'owner': request.user.pk,
        'name': name,
        'schema_name': schema_name.lower(),
        'organization': organization,
        'publicly_readable': False,
        'paid_until': datetime.datetime(2999, 12, 31),
    })
    if form.is_valid():
        return create_tenant(form, request)

    raise RuntimeError(form_errors_to_list(form))
