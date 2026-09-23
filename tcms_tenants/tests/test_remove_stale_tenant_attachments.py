# Copyright (c) 2026 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

# pylint: disable=too-many-ancestors

import shutil
from io import StringIO

from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db.models import IntegerField
from django.db.models.functions import Cast

from django_tenants.utils import (
    get_tenant_model,
    schema_exists,
    tenant_context,
)

from attachments.models import Attachment
from tcms.tests.factories import TestCaseFactory, TestExecutionFactory, TestPlanFactory

from tcms_tenants.storage import TenantFileSystemStorage
from tcms_tenants.tests import TenantGroupsTestCase


class RemoveStaleTenantAttachmentsTestCase(TenantGroupsTestCase):
    attachments_per_model = 100
    pk_offset = 1_000_000_000
    storage = TenantFileSystemStorage()

    @staticmethod
    def tenants_with_schema():
        tenants = []
        for tenant in get_tenant_model().objects.all():
            if schema_exists(tenant.schema_name):
                tenants.append(tenant)

        return tenants

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        for tenant in cls.tenants_with_schema():
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

        stale2 = Attachment.objects.create(
            content_type=content_type,
            object_id=parent_obj.pk,
            attachment_file=SimpleUploadedFile(
                f"stale2{index}.txt", b"attachment content"
            ),
            creator=cls.tester,
        )
        stale2.object_id = ""
        stale2.save()

    def test_removes_only_attachments_which_are_attached_to_missing_objects(self):
        tenants = self.tenants_with_schema()
        self.assertGreaterEqual(len(tenants), 1)

        for tenant in tenants:
            with tenant_context(tenant):
                self.assertTrue(
                    Attachment.objects.exclude(object_id="")
                    .annotate(object_id_as_int=Cast("object_id", IntegerField()))
                    .filter(object_id_as_int__gt=self.pk_offset)
                    .exists()
                )
                self.assertEqual(
                    Attachment.objects.count(), self.attachments_per_model * 3 * 3
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
                    Attachment.objects.exclude(object_id="")
                    .annotate(object_id_as_int=Cast("object_id", IntegerField()))
                    .filter(object_id_as_int__gt=self.pk_offset)
                    .exists()
                )

                remaining_files = sorted(
                    f"attachment{index}.txt"
                    for index in range(1, self.attachments_per_model + 1)
                )
                parents, _ = self.storage.listdir("attachments")
                self.assertEqual(len(parents), 3)

                for parent in parents:
                    dirs, _ = self.storage.listdir(f"attachments/{parent}")
                    self.assertEqual(len(dirs), 1)

                    for directory in dirs:
                        sub_dirs, files = self.storage.listdir(
                            f"attachments/{parent}/{directory}"
                        )
                        self.assertEqual(sub_dirs, [])
                        self.assertEqual(sorted(files), remaining_files)

            for banner in ("Removing attachments", "End removing attachments"):
                self.assertIn(
                    f"=== {banner} for tenant '{tenant.schema_name}' ===",
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
            self.storage.delete(missing.attachment_file.name)
            self.assertFalse(self.storage.exists(missing.attachment_file.name))
            self.assertTrue(self.storage.exists(kept.attachment_file.name))

            attachments_dir = f"attachments/testcases_testcase/{test_case.pk}"
            directory = self.storage.path(attachments_dir)

        self.addCleanup(shutil.rmtree, directory, True)

        out = StringIO()
        call_command(
            "remove_stale_tenant_attachments",
            answer="y",
            verbosity=1,
            stdout=out,
        )

        self.assertIn("with missing file", out.getvalue())

        with tenant_context(self.tenant):
            self.assertFalse(Attachment.objects.filter(pk=missing.pk).exists())
            self.assertTrue(Attachment.objects.filter(pk=kept.pk).exists())
            self.assertTrue(self.storage.exists(kept.attachment_file.name))
