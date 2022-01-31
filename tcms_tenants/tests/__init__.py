# Copyright (c) 2019-2022 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt

from django.db import connection, transaction
from django.db.utils import ProgrammingError
from django.conf import settings

import factory
from factory.django import DjangoModelFactory

from django_tenants.clone import CloneSchema
from django_tenants.test.client import TenantClient
from django_tenants.test.cases import FastTenantTestCase
from django_tenants.utils import get_tenant_model, schema_context, tenant_context

from tcms.tests.factories import TestPlanFactory
from tenant_groups.models import Group as TenantGroup


class UserFactory(DjangoModelFactory):
    class Meta:
        model = settings.AUTH_USER_MODEL

    # avoid conflicts with tcms.tests.factories.UserFactory
    username = factory.Sequence(lambda n: f"tenant-user{n}")
    first_name = factory.Sequence(lambda n: f"First{n}")
    last_name = factory.Sequence(lambda n: f"Last{n}-ov")
    email = factory.LazyAttribute(lambda user: f"{user.username}@kiwitcms.org")
    is_active = True
    is_staff = True
    is_superuser = False


class LoggedInTestCase(FastTenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "fast"

    @classmethod
    def setup_tenant(cls, tenant):
        super().setup_tenant(tenant)

        tenant.publicly_readable = False
        tenant.owner = UserFactory()
        tenant.owner.set_password('password')
        tenant.owner.save()

    @classmethod
    def setUpClass(cls):
        # b/c it may create a new tenant
        with schema_context('public'):
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


class TenantGroupsTestCase(LoggedInTestCase):
    original_value = None

    @classmethod
    def get_test_schema_name(cls):
        # NB: this is a special name, utils.create_tenant() will
        # use cloning if this schema exists which is faster
        return "empty"

    @classmethod
    def get_test_tenant_domain(cls):
        return "empty.test.com"

    @classmethod
    def get_verbosity(cls):
        return 1

    @classmethod
    def setUpClass(cls):
        # will create the actual schema
        cls.original_value = get_tenant_model().auto_create_schema
        get_tenant_model().auto_create_schema = True

        # execute before calling the parent class which will start a DB transaction
        with schema_context('public'):
            cursor = connection.cursor()

            try:
                cursor.execute("SELECT 'clone_schema'::regproc")
            except ProgrammingError:
                CloneSchema()._create_clone_schema_function()  # pylint: disable=protected-access
                transaction.commit()

            # tenant creation may happen here so it needs to be on public schema
            super().setUpClass()

        with tenant_context(cls.tenant):
            # add owner to default groups b/c they need certain permissions
            # and b/c this is what utils.create_tenant() does
            TenantGroup.objects.get(name="Administrator").user_set.add(cls.tenant.owner)
            TenantGroup.objects.get(name="Tester").user_set.add(cls.tenant.owner)

    @classmethod
    def tearDownClass(cls):
        get_tenant_model().auto_create_schema = cls.original_value
        super().tearDownClass()
