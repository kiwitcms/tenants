# Copyright (c) 2019-2026 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

# pylint: disable=too-many-ancestors
import os
import unittest

import requests
from botocore.exceptions import ClientError
from django.db import connection
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from storages.backends.s3 import S3Storage

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


class TenantDeleteTestCase(LoggedInTestCase):
    storage = TenantFileSystemStorage()

    @override_settings(
        MEDIA_ROOT="apps_dir/media",
        MEDIA_URL="/media/",
        MULTITENANT_RELATIVE_MEDIA_ROOT="%s",
    )
    def test_tenant_delete_removes_media_directory(self):
        connection.set_schema_to_public()
        tenant = utils.get_tenant_model()(
            schema_name="tenant2delete", owner=UserFactory(), name="To Delete"
        )
        tenant.save()

        # Save a file under this tenant schema's storage
        with utils.tenant_context(tenant):
            file_name = self.storage.save(
                "hello_delete.txt", ContentFile("Hello Delete")
            )
            # convert to absolute path
            file_name = self.storage.path(file_name)
            self.assertTrue(self.storage.exists(file_name))

            tenant_storage_dir = os.path.dirname(file_name)
            self.assertTrue(self.storage.exists(tenant_storage_dir))

        # Delete the tenant
        tenant.delete()

        # The tenant's storage directory (which includes the file) should be removed
        self.assertFalse(os.path.exists(file_name))
        self.assertFalse(os.path.exists(tenant_storage_dir))

    @override_settings(
        MEDIA_ROOT="apps_dir/media",
        MEDIA_URL="/media/",
        MULTITENANT_RELATIVE_MEDIA_ROOT="%s",
    )
    def test_tenant_delete_doesnt_raise_when_media_dir_doesnt_exist(
        self,
    ):  # pylint: disable=no-self-use
        connection.set_schema_to_public()
        tenant = utils.get_tenant_model()(
            schema_name="w0uploads", owner=UserFactory(), name="Without Uploads"
        )
        tenant.save()

        # no tenant relative dir, delete doesn't raise
        tenant.delete()


class S3StorageTests(SimpleTestCase):
    access_key = os.environ.get("AWS_S3_ACCESS_KEY_ID")
    secret_key = os.environ.get("AWS_S3_SECRET_ACCESS_KEY")
    bucket_name = os.environ.get("AWS_STORAGE_BUCKET_NAME")
    endpoint_url = os.environ.get("AWS_S3_ENDPOINT_URL")
    region_name = os.environ.get("AWS_S3_REGION_NAME")

    @classmethod
    def setUpClass(cls):
        if not all(
            (
                cls.access_key,
                cls.secret_key,
                cls.bucket_name,
                cls.endpoint_url,
                cls.region_name,
            )
        ):
            raise unittest.SkipTest("S3 environment variables are not configured")

        super().setUpClass()

        cls.storage = S3Storage(
            bucket_name=cls.bucket_name,
            endpoint_url=cls.endpoint_url,
            region_name=cls.region_name,
            addressing_style="path",
        )

        try:
            cls.storage.bucket.creation_date
        except ClientError:
            cls.storage.bucket.create()

    def test_upload_and_read_via_s3_endpoint(self):
        file_name = f"hello_world_{timezone.now().timestamp()}.txt"
        self.storage.save(file_name, ContentFile(b"Hello World"))

        response = requests.get(self.storage.url(file_name), timeout=10)

        self.assertEqual(200, response.status_code)
        self.assertEqual("Hello World", response.text)

    def test_delete_then_read_via_s3_endpoint(self):
        file_name = f"hello_world_{timezone.now().timestamp()}.txt"
        self.storage.save(file_name, ContentFile(b"Hello World"))

        self.storage.delete(file_name)

        response = requests.get(self.storage.url(file_name), timeout=10)

        self.assertEqual(404, response.status_code)
        self.assertIn("<Code>NoSuchKey</Code>", response.text)
