# Copyright (c) 2026 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

# pylint: disable=too-many-ancestors,no-self-use

import os
import shutil
import unittest
from datetime import timedelta
from io import StringIO

from django.contrib.contenttypes.models import ContentType
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone

from botocore.exceptions import ClientError
from storages.utils import safe_join as storages_safe_join

from django_tenants.utils import tenant_context

from attachments.models import Attachment
from tcms.tests.factories import TestCaseFactory

from tcms_tenants.tests import TenantGroupsTestCase, tenants_with_schema


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
class RemoveAttachmentsOlderThanTestCase(TenantGroupsTestCase):
    def file_reference(self, name):
        return default_storage.path(name)

    def directory_reference(self, file_reference):
        directory = os.path.dirname(file_reference)
        if not directory.endswith("/"):
            directory += "/"
        return directory

    def assertPathExistsViaStorageBackend(  # pylint: disable=invalid-name
        self, path, expected
    ):
        self.assertEqual(expected, default_storage.exists(path))

    def remove_attachment_storage(self, directory_reference):
        shutil.rmtree(directory_reference, True)

    def add_attachment(self, tenant, file_name, days):
        with tenant_context(tenant):
            parent_obj = TestCaseFactory()
            content_type = ContentType.objects.get_for_model(parent_obj)
            attachment = Attachment.objects.create(
                content_type=content_type,
                object_id=parent_obj.pk,
                attachment_file=SimpleUploadedFile(file_name, b"attachment content"),
                creator=self.tester,
            )

            attachment.created = timezone.now() - timedelta(days=days)
            attachment.save()

            attachment_dir = self.directory_reference(
                self.file_reference(attachment.attachment_file.name)
            )
            self.addCleanup(self.remove_attachment_storage, attachment_dir)

            return attachment

    def test_removes_attachments_older_than_days(self):
        seeded = {}
        for tenant in tenants_with_schema():
            seeded[tenant.schema_name] = (
                self.add_attachment(tenant, "old.txt", days=30),
                self.add_attachment(tenant, "new.txt", days=1),
            )

        out = StringIO()
        call_command(
            "remove_attachments_older_than",
            days=7,
            answer="y",
            verbosity=1,
            stdout=out,
        )

        output = out.getvalue()

        for tenant in tenants_with_schema():
            for banner in (
                "Removing attachments older than 7 days",
                "End removing attachments older than 7 days",
            ):
                self.assertIn(
                    f"=== {banner} for tenant '{tenant.schema_name}' ===",
                    output,
                )

            old, new = seeded[tenant.schema_name]
            with tenant_context(tenant):
                self.assertFalse(Attachment.objects.filter(pk=old.pk).exists())
                self.assertTrue(Attachment.objects.filter(pk=new.pk).exists())
                self.assertPathExistsViaStorageBackend(
                    self.file_reference(old.attachment_file.name), False
                )
                self.assertPathExistsViaStorageBackend(
                    self.file_reference(new.attachment_file.name), True
                )

    def test_only_selected_tenant_is_affected(self):
        seeded = {}
        for tenant in tenants_with_schema():
            seeded[tenant.schema_name] = self.add_attachment(tenant, "old.txt", days=30)

        selected = tenants_with_schema()[0]
        out = StringIO()
        call_command(
            "remove_attachments_older_than",
            tenant=selected.schema_name,
            days=7,
            answer="y",
            verbosity=1,
            stdout=out,
        )

        output = out.getvalue()
        self.assertIn(f"for tenant '{selected.schema_name}'", output)

        for tenant in tenants_with_schema():
            with tenant_context(tenant):
                if tenant.schema_name == selected.schema_name:
                    self.assertFalse(
                        Attachment.objects.filter(
                            pk=seeded[tenant.schema_name].pk
                        ).exists()
                    )
                else:
                    self.assertNotIn(f"for tenant '{tenant.schema_name}'", output)
                    self.assertTrue(
                        Attachment.objects.filter(
                            pk=seeded[tenant.schema_name].pk
                        ).exists()
                    )
                    self.assertPathExistsViaStorageBackend(
                        self.file_reference(
                            seeded[tenant.schema_name].attachment_file.name
                        ),
                        True,
                    )


@override_settings(
    MULTITENANT_RELATIVE_MEDIA_ROOT="%s",
    STORAGES={
        "default": {
            "BACKEND": "tcms_tenants.storage.TenantS3Storage",
            "OPTIONS": {
                "access_key": os.environ.get("AWS_S3_ACCESS_KEY_ID"),
                "secret_key": os.environ.get("AWS_S3_SECRET_ACCESS_KEY"),
                "bucket_name": os.environ.get("AWS_STORAGE_BUCKET_NAME"),
                "endpoint_url": os.environ.get("AWS_S3_ENDPOINT_URL"),
                "region_name": os.environ.get("AWS_S3_REGION_NAME"),
                "addressing_style": "path",
                "verify": os.environ.get("AWS_S3_VERIFY"),
            },
        },
    },
)
class RemoveAttachmentsOlderThanTestCaseOnS3(RemoveAttachmentsOlderThanTestCase):
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

        try:
            default_storage.bucket.create()
        except ClientError as error:
            if error.response["Error"]["Code"] not in (
                "BucketAlreadyOwnedByYou",
                "BucketAlreadyExists",
            ):
                raise

    def file_reference(self, name):
        return storages_safe_join(default_storage.location, name)

    def assertPathExistsViaStorageBackend(  # pylint: disable=invalid-name
        self, path, expected
    ):
        try:
            default_storage.bucket.Object(path).load()
        except ClientError as error:
            if error.response["ResponseMetadata"]["HTTPStatusCode"] == 404:
                self.assertEqual(expected, False)
                return
            raise

        self.assertEqual(expected, True)

    def remove_attachment_storage(self, directory_reference):
        objects = default_storage.bucket.objects.filter(Prefix=directory_reference)
        for obj in objects:
            obj.delete()
