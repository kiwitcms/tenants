# Copyright (c) 2019-2021 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt

from django.conf import settings

import factory
from factory.django import DjangoModelFactory

from django_tenants.test.client import TenantClient
from django_tenants.test.cases import FastTenantTestCase
from django_tenants.utils import tenant_context

from tcms.tests.factories import TestPlanFactory


class UserFactory(DjangoModelFactory):
    class Meta:
        model = settings.AUTH_USER_MODEL

    username = factory.Sequence(lambda n: f"User{n}")
    first_name = factory.Sequence(lambda n: f"First{n}")
    last_name = factory.Sequence(lambda n: f"Last{n}-ov")
    email = factory.LazyAttribute(lambda user: f"{user.username}@kiwitcms.org")
    is_active = True
    is_staff = True
    is_superuser = False


class LoggedInTestCase(FastTenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return 'fast'

    @classmethod
    def get_test_tenant_domain(cls):
        return 'tenant.fast-test.com'

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.publicly_readable = False
        tenant.owner = UserFactory()
        tenant.owner.set_password('password')
        tenant.owner.save()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # authorize tenant owner
        cls.tenant.authorized_users.add(cls.tenant.owner)

        cls.tester = UserFactory()
        cls.tester.set_password('password')
        cls.tester.save()

        # authorize this user
        cls.tenant.authorized_users.add(cls.tester)

        # initial data
        with tenant_context(cls.tenant):
            cls.test_plan_by_owner = TestPlanFactory(author=cls.tenant.owner)

    def setUp(self):
        super().setUp()

        self.client = TenantClient(self.tenant)
        self.client.login(username=self.tester.username,  # nosec:B106:hardcoded_password_funcarg
                          password='password')
