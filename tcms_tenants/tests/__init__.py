# Copyright (c) 2019 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt

from django.conf import settings

import factory
from factory.django import DjangoModelFactory

from django_tenants.test.client import TenantClient
from django_tenants.test.cases import TenantTestCase


class UserFactory(DjangoModelFactory):
    class Meta:
        model = settings.AUTH_USER_MODEL

    username = factory.Sequence(lambda n: 'User%d' % n)
    email = factory.LazyAttribute(lambda user: '%s@kiwitcms.org' % user.username)
    is_active = True
    is_staff = True


class LoggedInTestCase(TenantTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

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
