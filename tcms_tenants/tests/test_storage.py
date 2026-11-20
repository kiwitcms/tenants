# Copyright (c) 2019-2026 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

# pylint: disable=too-many-ancestors
import json
import os
import unittest
from http import HTTPStatus
from urllib.parse import urlparse

import requests
from botocore.exceptions import ClientError
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.conf import settings
from django.db import connection
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from storages.backends.s3 import S3Storage

from django_tenants import utils

from tcms_tenants.storage import TenantFileSystemStorage, TenantS3Storage
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


@override_settings(
    MEDIA_ROOT="apps_dir/media",
    MEDIA_URL="/media/",
    MULTITENANT_RELATIVE_MEDIA_ROOT="%s",
    STORAGES={
        "default": {
            "BACKEND": "tcms_tenants.storage.TenantFileSystemStorage",
        },
    },
)
class TenantDeleteTestCase(LoggedInTestCase):
    def assertPathExistsViaStorageBackend(  # pylint: disable=invalid-name
        self, path, expected
    ):
        self.assertEqual(expected, default_storage.exists(path))

    def assertPathExistsViaExternalCheck(  # pylint: disable=invalid-name
        self, path, expected
    ):
        self.assertEqual(expected, os.path.exists(path))

    def test_tenant_delete_removes_media_directory(self):
        connection.set_schema_to_public()
        tenant = utils.get_tenant_model()(
            schema_name="tenant2delete", owner=UserFactory(), name="To Delete"
        )
        tenant.save()

        # Save a file under this tenant schema's storage
        with utils.tenant_context(tenant):
            file_name = default_storage.save(
                "hello_delete.txt", ContentFile("Hello Delete")
            )
            # convert to absolute path
            file_name = default_storage.path(file_name)
            self.assertPathExistsViaStorageBackend(file_name, True)

            tenant_storage_dir = os.path.dirname(file_name)
            if not tenant_storage_dir.endswith("/"):
                tenant_storage_dir += "/"
            self.assertPathExistsViaStorageBackend(tenant_storage_dir, True)

        # Delete the tenant
        tenant.delete()

        # The tenant's storage directory (which includes the file) should be removed
        self.assertPathExistsViaExternalCheck(file_name, False)
        self.assertPathExistsViaExternalCheck(tenant_storage_dir, False)

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
    verify = os.environ.get("AWS_S3_VERIFY")

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
            access_key=cls.access_key,
            secret_key=cls.secret_key,
            bucket_name=cls.bucket_name,
            endpoint_url=cls.endpoint_url,
            region_name=cls.region_name,
            addressing_style="path",
            verify=cls.verify,
        )

        try:
            cls.storage.bucket.create()
        except ClientError as error:
            if error.response["Error"]["Code"] not in (
                "BucketAlreadyOwnedByYou",
                "BucketAlreadyExists",
            ):
                raise

    def _get(self, url):  # pylint: disable=no-self-use
        return requests.get(url, timeout=10, verify=self.verify)

    def test_upload_and_read_via_s3_endpoint(self):
        file_name = f"hello_world_{timezone.now().timestamp()}.txt"
        self.storage.save(file_name, ContentFile(b"Hello World"))

        response = self._get(self.storage.url(file_name))

        self.assertEqual(HTTPStatus.OK, response.status_code)
        self.assertEqual("Hello World", response.text)

    def test_delete_then_read_via_s3_endpoint(self):
        file_name = f"hello_world_{timezone.now().timestamp()}.txt"
        self.storage.save(file_name, ContentFile(b"Hello World"))

        self.storage.delete(file_name)

        response = self._get(self.storage.url(file_name))

        self.assertEqual(HTTPStatus.NOT_FOUND, response.status_code)
        self.assertIn("<Code>NoSuchKey</Code>", response.text)


class CloudFrontSignedURLTests(S3StorageTests):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.cloudfront_key = key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode()

        endpoint = urlparse(cls.endpoint_url)
        cls.storage = S3Storage(
            access_key=cls.access_key,
            secret_key=cls.secret_key,
            bucket_name=cls.bucket_name,
            endpoint_url=cls.endpoint_url,
            region_name=cls.region_name,
            addressing_style="path",
            verify=cls.verify,
            custom_domain=f"{endpoint.netloc}/{cls.bucket_name}",
            url_protocol=f"{endpoint.scheme}:",
            cloudfront_key_id="test-key",
            cloudfront_key=cls.cloudfront_key,
        )

        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{cls.bucket_name}/*",
                }
            ],
        }
        cls.storage.connection.meta.client.put_bucket_policy(
            Bucket=cls.bucket_name, Policy=json.dumps(policy)
        )

    def _get(self, url):
        self.assertIn("Key-Pair-Id=test-key", url)
        # CloudFront validates the signature and forwards only the path to the origin
        return super()._get(url.split("?", 1)[0])


class TenantS3StorageTestCase(LoggedInTestCase):
    access_key = os.environ.get("AWS_S3_ACCESS_KEY_ID")
    secret_key = os.environ.get("AWS_S3_SECRET_ACCESS_KEY")
    bucket_name = os.environ.get("AWS_STORAGE_BUCKET_NAME")
    endpoint_url = os.environ.get("AWS_S3_ENDPOINT_URL")
    region_name = os.environ.get("AWS_S3_REGION_NAME")
    verify = os.environ.get("AWS_S3_VERIFY")

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

        cls.storage = TenantS3Storage(
            access_key=cls.access_key,
            secret_key=cls.secret_key,
            bucket_name=cls.bucket_name,
            endpoint_url=cls.endpoint_url,
            region_name=cls.region_name,
            addressing_style="path",
            verify=cls.verify,
        )

        try:
            cls.storage.bucket.create()
        except ClientError as error:
            if error.response["Error"]["Code"] not in (
                "BucketAlreadyOwnedByYou",
                "BucketAlreadyExists",
            ):
                raise

    @override_settings(MULTITENANT_RELATIVE_MEDIA_ROOT="%s")
    def test_files_are_saved_under_subdirectories_per_tenant(self):
        connection.set_schema_to_public()
        timestamp = timezone.now().timestamp()
        tenant2 = utils.get_tenant_model()(schema_name="tenant2", owner=UserFactory())
        tenant2.save()

        domain2 = utils.get_tenant_domain_model()(tenant=tenant2, domain="example.com")
        domain2.save()

        self.assertEqual("public", self.storage.location)
        public_file_name = self.storage.save(
            f"hello_world_{timestamp}.txt", ContentFile("Hello World")
        )
        public_url = self.storage.url(public_file_name)

        with utils.tenant_context(self.tenant):
            self.assertEqual("fast", self.storage.location)
            t1_file_name = self.storage.save(
                f"hello_from_1_{timestamp}.txt", ContentFile("Hello T1")
            )
            t1_url = self.storage.url(t1_file_name)

        with utils.tenant_context(tenant2):
            self.assertEqual("tenant2", self.storage.location)
            t2_file_name = self.storage.save(
                f"hello_from_2_{timestamp}.txt", ContentFile("Hello T2")
            )
            t2_url = self.storage.url(t2_file_name)

        # assert urls are correct
        self.assertIn("/public/", public_url)
        self.assertIn("/fast/", t1_url)
        self.assertIn("/tenant2/", t2_url)

        # assert contents are correct
        response = requests.get(public_url, timeout=10, verify=self.verify)
        self.assertEqual(HTTPStatus.OK, response.status_code)
        self.assertEqual("Hello World", response.text)

        response = requests.get(t1_url, timeout=10, verify=self.verify)
        self.assertEqual(HTTPStatus.OK, response.status_code)
        self.assertEqual("Hello T1", response.text)

        response = requests.get(t2_url, timeout=10, verify=self.verify)
        self.assertEqual(HTTPStatus.OK, response.status_code)
        self.assertEqual("Hello T2", response.text)


@override_settings(
    MULTITENANT_RELATIVE_MEDIA_ROOT="%s",
    STORAGES={
        **settings.STORAGES,
        "default": {
            "BACKEND": "tcms_tenants.storage.TenantS3Storage",
            "OPTIONS": {
                "bucket_name": os.environ.get("AWS_STORAGE_BUCKET_NAME"),
                "endpoint_url": os.environ.get("AWS_S3_ENDPOINT_URL"),
                "region_name": os.environ.get("AWS_S3_REGION_NAME"),
                "addressing_style": "path",
                "verify": os.environ.get("AWS_S3_VERIFY"),
            },
        },
    },
)
class TenantS3DeleteTestCase(TenantDeleteTestCase):

    access_key = os.environ.get("AWS_S3_ACCESS_KEY_ID")
    secret_key = os.environ.get("AWS_S3_SECRET_ACCESS_KEY")
    bucket_name = os.environ.get("AWS_STORAGE_BUCKET_NAME")
    endpoint_url = os.environ.get("AWS_S3_ENDPOINT_URL")
    region_name = os.environ.get("AWS_S3_REGION_NAME")
    verify = os.environ.get("AWS_S3_VERIFY")

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

        # django_tenants' TenantTestCase.setUpClass() doesn't call super(), so
        # Django never activates the class-level override_settings().
        # pylint: disable-next=not-a-mapping
        cls.enterClassContext(override_settings(**cls._overridden_settings))

        cls.storage = TenantS3Storage(
            bucket_name=cls.bucket_name,
            endpoint_url=cls.endpoint_url,
            region_name=cls.region_name,
            addressing_style="path",
            verify=cls.verify,
        )

        try:
            cls.storage.bucket.create()
        except ClientError as error:
            if error.response["Error"]["Code"] not in (
                "BucketAlreadyOwnedByYou",
                "BucketAlreadyExists",
            ):
                raise

    def assertPathExistsViaStorageBackend(  # pylint: disable=invalid-name
        self, path, expected
    ):
        if path.endswith("/"):
            # S3 has no directories. A non-empty key prefix is the closest
            # equivalent. listdir() returns ([], []) for a non-existing prefix.
            directories, files = self.storage.listdir(path)
            exists = bool(directories or files)
        else:
            try:
                self.storage.size(path)
            except FileNotFoundError:
                exists = False
            else:
                exists = True

        self.assertEqual(expected, exists)

    def assertPathExistsViaExternalCheck(  # pylint: disable=invalid-name
        self, path, expected
    ):
        response = requests.get(self.storage.url(path), timeout=10, verify=self.verify)
        self.assertIn(response.status_code, (HTTPStatus.OK, HTTPStatus.NOT_FOUND))
        self.assertEqual(expected, response.status_code == HTTPStatus.OK)

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
            directory = "./"

            self.assertPathExistsViaStorageBackend(file_name, True)
            self.assertPathExistsViaStorageBackend(directory, True)

        # Delete the tenant
        tenant.delete()

        with utils.tenant_context(tenant):
            self.assertPathExistsViaExternalCheck(file_name, False)
            self.assertPathExistsViaExternalCheck(directory, False)

    def test_tenant_delete_doesnt_raise_when_media_dir_doesnt_exist(self):
        connection.set_schema_to_public()
        tenant = utils.get_tenant_model()(
            schema_name="w0uploads", owner=UserFactory(), name="Without Uploads"
        )
        tenant.save()

        # no tenant relative prefix, delete doesn't raise
        tenant.delete()
