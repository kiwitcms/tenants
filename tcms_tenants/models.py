# Copyright (c) 2019 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt

from django.db import models
from django.conf import settings
from django_tenants.models import TenantMixin, DomainMixin


class Tenant(TenantMixin):
    auto_create_schema = True
    auto_drop_schema = True

    name = models.CharField(max_length=100, db_index=True)
    created_on = models.DateField(auto_now_add=True, db_index=True)
    paid_until =  models.DateField(null=True, blank=True, db_index=True)
    on_trial = models.BooleanField(default=True, db_index=True)
    authorized_users = models.ManyToManyField(to=settings.AUTH_USER_MODEL)

    def __str__(self):
        return "[%s] %s" % (self.schema_name, self.name)


def _authorized_user_str(self):
    return "%s@%s" % (self.user.username, self.tenant.name)


Tenant.authorized_users.through.__str__ = _authorized_user_str


class Domain(DomainMixin):
    def __str__(self):
        return "%s for %s" % (self.domain, self.tenant)
