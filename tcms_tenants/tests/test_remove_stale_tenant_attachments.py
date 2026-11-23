# Copyright (c) 2026 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

# pylint: disable=too-many-ancestors,no-self-use

import os
import shutil
import unittest
from io import StringIO

from django.contrib.contenttypes.models import ContentType
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db.models import IntegerField
from django.db.models.functions import Cast
from django.test import override_settings

from botocore.exceptions import ClientError
from storages.utils import safe_join as storages_safe_join

from django_tenants.utils import tenant_context

from attachments.models import Attachment
from tcms.tests.factories import TestCaseFactory, TestExecutionFactory, TestPlanFactory

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
class RemoveStaleTenantAttachmentsTestCase(TenantGroupsTestCase):
    attachments_per_model = 100
    pk_offset = 1_000_000_000

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

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        for tenant in tenants_with_schema():
            with tenant_context(tenant):
                # note: sending emails is disabled
                test_execution = TestExecutionFactory()

                test_case = TestCaseFactory()
                test_case.save()
                test_case.emailing.notify_on_case_update = False
                test_case.emailing.save()

                test_plan = TestPlanFactory()
                test_plan.save()
                test_plan.emailing.notify_on_plan_update = False
                test_plan.emailing.save()

                for i in range(1, cls.attachments_per_model + 1):
                    cls.add_attachments(test_case, i)
                    cls.add_attachments(test_execution, i)
                    cls.add_attachments(test_plan, i)

    @classmethod
    def add_attachments(cls, parent_obj, index):
        content_type = ContentType.objects.get_for_model(parent_obj)

        _ = Attachment.objects.create(
            content_type=content_type,
            object_id=parent_obj.pk,
            attachment_file=SimpleUploadedFile(
                f"attachment{index}.txt", b"attachment content"
            ),
            creator=cls.tester,
        )

        stale = Attachment.objects.create(
            content_type=content_type,
            object_id=parent_obj.pk,
            attachment_file=SimpleUploadedFile(
                f"stale{index}.txt", b"attachment content"
            ),
            creator=cls.tester,
        )
        stale.object_id = str(int(parent_obj.pk) + cls.pk_offset)
        stale.save()

    def test_removes_only_attachments_which_are_attached_to_missing_objects(self):
        tenants = tenants_with_schema()
        self.assertGreaterEqual(len(tenants), 1)

        for tenant in tenants:
            with tenant_context(tenant):
                self.assertTrue(
                    Attachment.objects.annotate(
                        object_id_as_int=Cast("object_id", IntegerField())
                    )
                    .filter(object_id_as_int__gt=self.pk_offset)
                    .exists()
                )
                self.assertEqual(
                    Attachment.objects.count(), self.attachments_per_model * 2 * 3
                )

        out = StringIO()
        call_command(
            "remove_stale_tenant_attachments",
            answer="y",
            verbosity=1,
            stdout=out,
        )

        output = out.getvalue()

        for tenant in tenants:
            with tenant_context(tenant):
                self.assertEqual(
                    Attachment.objects.count(), self.attachments_per_model * 3
                )
                self.assertFalse(
                    Attachment.objects.annotate(
                        object_id_as_int=Cast("object_id", IntegerField())
                    )
                    .filter(object_id_as_int__gt=self.pk_offset)
                    .exists()
                )

                remaining_files = sorted(
                    f"attachment{index}.txt"
                    for index in range(1, self.attachments_per_model + 1)
                )
                parents, _ = default_storage.listdir("attachments")
                self.assertEqual(len(parents), 3)

                for parent in parents:
                    dirs, _ = default_storage.listdir(f"attachments/{parent}")
                    self.assertEqual(len(dirs), 1)

                    for directory in dirs:
                        sub_dirs, files = default_storage.listdir(
                            f"attachments/{parent}/{directory}"
                        )
                        self.assertEqual(sub_dirs, [])
                        self.assertEqual(sorted(files), remaining_files)

            for banner in ("Removing attachments", "End removing attachments"):
                self.assertIn(
                    f"=== {banner} for tenant '{tenant.schema_name}' ===",
                    output,
                )

    def test_dry_run_removes_nothing(self):
        tenants = tenants_with_schema()
        self.assertGreaterEqual(len(tenants), 1)

        out = StringIO()
        call_command(
            "remove_stale_tenant_attachments",
            answer="y",
            dry_run=True,
            verbosity=1,
            stdout=out,
        )

        output = out.getvalue()

        for tenant in tenants:
            with tenant_context(tenant):
                self.assertEqual(
                    Attachment.objects.count(), self.attachments_per_model * 2 * 3
                )
                self.assertTrue(
                    Attachment.objects.annotate(
                        object_id_as_int=Cast("object_id", IntegerField())
                    )
                    .filter(object_id_as_int__gt=self.pk_offset)
                    .exists()
                )

            self.assertIn(
                f"for tenant '{tenant.schema_name}' === dry run: True ===",
                output,
            )

    def test_removes_attachments_whose_file_is_missing(self):
        with tenant_context(self.tenant):
            test_case = TestCaseFactory()
            content_type = ContentType.objects.get_for_model(test_case)

            missing = Attachment.objects.create(
                content_type=content_type,
                object_id=test_case.pk,
                attachment_file=SimpleUploadedFile(
                    "missing.txt", b"attachment content"
                ),
                creator=self.tester,
            )
            kept = Attachment.objects.create(
                content_type=content_type,
                object_id=test_case.pk,
                attachment_file=SimpleUploadedFile("kept.txt", b"attachment content"),
                creator=self.tester,
            )

            # delete the file from disk, keep the object and its parent object
            default_storage.delete(missing.attachment_file.name)
            self.assertPathExistsViaStorageBackend(
                self.file_reference(missing.attachment_file.name), False
            )
            self.assertPathExistsViaStorageBackend(
                self.file_reference(kept.attachment_file.name), True
            )

            directory = self.directory_reference(
                self.file_reference(kept.attachment_file.name)
            )
            self.addCleanup(self.remove_attachment_storage, directory)

        out = StringIO()
        call_command(
            "remove_stale_tenant_attachments",
            answer="y",
            check_storage=True,
            verbosity=1,
            stdout=out,
        )

        self.assertIn("with missing file", out.getvalue())

        with tenant_context(self.tenant):
            self.assertFalse(Attachment.objects.filter(pk=missing.pk).exists())
            self.assertTrue(Attachment.objects.filter(pk=kept.pk).exists())
            self.assertPathExistsViaStorageBackend(
                self.file_reference(kept.attachment_file.name), True
            )

    def test_keeps_attachments_with_missing_file_without_check_storage(self):
        with tenant_context(self.tenant):
            test_case = TestCaseFactory()
            content_type = ContentType.objects.get_for_model(test_case)

            missing = Attachment.objects.create(
                content_type=content_type,
                object_id=test_case.pk,
                attachment_file=SimpleUploadedFile("missing.txt", b"content"),
                creator=self.tester,
            )
            default_storage.delete(missing.attachment_file.name)
            self.assertPathExistsViaStorageBackend(
                self.file_reference(missing.attachment_file.name), False
            )

            directory = self.directory_reference(
                self.file_reference(missing.attachment_file.name)
            )
            self.addCleanup(self.remove_attachment_storage, directory)

        out = StringIO()
        call_command(
            "remove_stale_tenant_attachments",
            answer="y",
            verbosity=1,
            stdout=out,
        )

        self.assertNotIn("with missing file", out.getvalue())

        with tenant_context(self.tenant):
            self.assertTrue(Attachment.objects.filter(pk=missing.pk).exists())


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
class RemoveStaleTenantAttachmentsOnS3(RemoveStaleTenantAttachmentsTestCase):
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
