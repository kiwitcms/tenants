# Copyright (c) 2019 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt

from django.conf import settings

import factory
from factory.django import DjangoModelFactory

from django_tenants.test.client import TenantClient
from django_tenants.test.cases import FastTenantTestCase


class UserFactory(DjangoModelFactory):
    class Meta:
        model = settings.AUTH_USER_MODEL

    username = factory.Sequence(lambda n: 'User%d' % n)
    first_name = factory.Sequence(lambda n: 'First%d' % n)
    last_name = factory.Sequence(lambda n: 'Last%d-ov' % n)
    email = factory.LazyAttribute(lambda user: '%s@kiwitcms.org' % user.username)
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

    def setUp(self):
        super().setUp()

        self.client = TenantClient(self.tenant)
        self.client.login(username=self.tester.username,  # nosec:B106:hardcoded_password_funcarg
                          password='password')
