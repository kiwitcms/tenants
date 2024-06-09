# Copyright (c) 2019-2024 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

import os

from django.db import models
from django.conf import settings

from django_tenants.models import TenantMixin, DomainMixin


class Tenant(TenantMixin):
    auto_create_schema = bool(os.environ.get("AUTO_CREATE_SCHEMA", True))
    auto_drop_schema = True

    name = models.CharField(max_length=100, db_index=True)
    created_on = models.DateTimeField(auto_now_add=True, db_index=True)
    paid_until = models.DateTimeField(null=True, blank=True, db_index=True)
    publicly_readable = models.BooleanField(default=False, db_index=True)
    authorized_users = models.ManyToManyField(to=settings.AUTH_USER_MODEL)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tenant_owner"
    )
    organization = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    extra_emails = models.CharField(
        null=True, blank=True, db_index=True, max_length=256
    )

    def __str__(self):
        return f"[{self.schema_name}] {self.name}"


def _authorized_user_str(self):
    return f"{self.user.username}@{self.tenant.name}"


Tenant.authorized_users.through.__str__ = _authorized_user_str


class Domain(DomainMixin):
    def __str__(self):
        return f"{self.domain} for {self.tenant}"
