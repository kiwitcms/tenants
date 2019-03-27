from django.db import models
from django_tenants.models import TenantMixin, DomainMixin


class Tenant(TenantMixin):
    # schema will be automatically created and synced when it is saved
    auto_create_schema = True

    name = models.CharField(max_length=100)
    created_on = models.DateField(auto_now_add=True)
    paid_until =  models.DateField()
    on_trial = models.BooleanField(default=False)


class Domain(DomainMixin):
    pass
