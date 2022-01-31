# Copyright (c) 2022 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt

import sys
import unittest

from django.core.management.base import BaseCommand
from django_tenants.utils import (
    get_public_schema_name,
    get_tenant_model,
    schema_context,
    tenant_context,
)

from tenant_groups.models import Group as TenantGroup


class Command(BaseCommand):
    def handle(self, **options):
        suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
        unittest.TextTestRunner().run(suite)


class TestDefaultTenantGroups(unittest.TestCase):
    public_schema = get_public_schema_name()

    def test_no_tenant_groups_were_created_on_public_schema(self):
        with schema_context(self.public_schema):
            self.assertFalse(TenantGroup.objects.exists())

    def test_tenant_groups_were_created_for_tenant_schemas(self):
        # inspect every tenant except
        for tenant in get_tenant_model().objects.exclude(schema_name=self.public_schema):
            with tenant_context(tenant):
                self.assertTrue(TenantGroup.objects.filter(name="Administrator").exists())
                self.assertTrue(TenantGroup.objects.filter(name="Tester").exists())
