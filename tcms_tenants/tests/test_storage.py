# Copyright (c) 2019 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt

from django.db import connection
from django.core.files.base import ContentFile
from django.test import override_settings

from django_tenants import utils
from django_tenants.test.cases import TenantTestCase

from tcms_tenants.storage import TenantFileSystemStorage
from tcms_tenants.tests import UserFactory


class TenantFileSystemStorageTestCase(TenantTestCase):
    @classmethod
    def setup_tenant(cls, tenant):
        tenant.owner = UserFactory()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # authorize tenant owner
        cls.tenant.authorized_users.add(cls.tenant.owner)

    @override_settings(MEDIA_ROOT="apps_dir/media",
                       MEDIA_URL="/media/",
                       MULTITENANT_RELATIVE_MEDIA_ROOT="%s")
    def test_files_are_saved_under_subdirectories_per_tenant(self):
        storage = TenantFileSystemStorage()

        connection.set_schema_to_public()
        tenant1 = utils.get_tenant_model()(schema_name='tenant1', owner=UserFactory())
        tenant1.save()

        domain1 = utils.get_tenant_domain_model()(tenant=tenant1, domain='something.test.com')
        domain1.save()

        connection.set_schema_to_public()
        tenant2 = utils.get_tenant_model()(schema_name='tenant2', owner=UserFactory())
        tenant2.save()

        domain2 = utils.get_tenant_domain_model()(tenant=tenant2, domain='example.com')
        domain2.save()

        # this file should be saved on the public schema
        public_file_name = storage.save('hello_world.txt', ContentFile('Hello World'))
        public_os_path = storage.path(public_file_name)
        public_url = storage.url(public_file_name)

        # switch to tenant1
        with utils.tenant_context(tenant1):
            t1_file_name = storage.save('hello_from_1.txt', ContentFile('Hello T1'))
            t1_os_path = storage.path(t1_file_name)
            t1_url = storage.url(t1_file_name)

        # switch to tenant2
        with utils.tenant_context(tenant2):
            t2_file_name = storage.save('hello_from_2.txt', ContentFile('Hello T2'))
            t2_os_path = storage.path(t2_file_name)
            t2_url = storage.url(t2_file_name)

        # assert the paths are correct
        self.assertTrue(public_os_path.endswith('apps_dir/media/public/%s' % public_file_name))
        self.assertTrue(t1_os_path.endswith('apps_dir/media/tenant1/%s' % t1_file_name))
        self.assertTrue(t2_os_path.endswith('apps_dir/media/tenant2/%s' % t2_file_name))

        # assert urls are correct
        self.assertEqual(public_url, '/media/public/%s' % public_file_name)
        self.assertEqual(t1_url, '/media/tenant1/%s' % t1_file_name)
        self.assertEqual(t2_url, '/media/tenant2/%s' % t2_file_name)

        # assert contents are correct
        with open(public_os_path, 'r') as fobj:
            self.assertEqual(fobj.read(), 'Hello World')

        with open(t1_os_path, 'r') as fobj:
            self.assertEqual(fobj.read(), 'Hello T1')

        with open(t2_os_path, 'r') as fobj:
            self.assertEqual(fobj.read(), 'Hello T2')
