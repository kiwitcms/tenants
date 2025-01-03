# Copyright (c) 2019-2025 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

# pylint: disable=too-many-ancestors
from django.db import connection
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import override_settings

from django_tenants import utils

from tcms_tenants.storage import TenantFileSystemStorage
from tcms_tenants.tests import LoggedInTestCase, UserFactory


class TenantFileSystemStorageTestCase(LoggedInTestCase):
    storage = TenantFileSystemStorage()

    @override_settings(
        MEDIA_ROOT="apps_dir/media",
        MEDIA_URL="/media/",
        MULTITENANT_RELATIVE_MEDIA_ROOT="%s",
    )
    def test_files_are_saved_under_subdirectories_per_tenant(self):
        connection.set_schema_to_public()
        tenant2 = utils.get_tenant_model()(schema_name="tenant2", owner=UserFactory())
        tenant2.save()

        domain2 = utils.get_tenant_domain_model()(tenant=tenant2, domain="example.com")
        domain2.save()

        # this file should be saved on the public schema
        public_file_name = self.storage.save(
            "hello_world.txt", ContentFile("Hello World")
        )
        public_os_path = self.storage.path(public_file_name)
        public_url = self.storage.url(public_file_name)

        # switch to tenant1
        with utils.tenant_context(self.tenant):
            t1_file_name = self.storage.save(
                "hello_from_1.txt", ContentFile("Hello T1")
            )
            t1_os_path = self.storage.path(t1_file_name)
            t1_url = self.storage.url(t1_file_name)

        # switch to tenant2
        with utils.tenant_context(tenant2):
            t2_file_name = self.storage.save(
                "hello_from_2.txt", ContentFile("Hello T2")
            )
            t2_os_path = self.storage.path(t2_file_name)
            t2_url = self.storage.url(t2_file_name)

        # assert the paths are correct
        self.assertTrue(
            public_os_path.endswith(f"apps_dir/media/public/{public_file_name}")
        )
        self.assertTrue(t1_os_path.endswith(f"apps_dir/media/fast/{t1_file_name}"))
        self.assertTrue(t2_os_path.endswith(f"apps_dir/media/tenant2/{t2_file_name}"))

        # assert urls are correct
        self.assertEqual(public_url, f"/media/public/{public_file_name}")
        self.assertEqual(t1_url, f"/media/fast/{t1_file_name}")
        self.assertEqual(t2_url, f"/media/tenant2/{t2_file_name}")

        # assert contents are correct
        with open(public_os_path, "r", encoding="utf-8") as fobj:
            self.assertEqual(fobj.read(), "Hello World")

        with open(t1_os_path, "r", encoding="utf-8") as fobj:
            self.assertEqual(fobj.read(), "Hello T1")

        with open(t2_os_path, "r", encoding="utf-8") as fobj:
            self.assertEqual(fobj.read(), "Hello T2")


class DefaultStorageTestCase(TenantFileSystemStorageTestCase):
    """
    Should result in the same behavior confirming that default
    settings have been applied correctly!
    """

    storage = default_storage
