# Copyright (c) 2026 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

# pylint: disable=too-many-ancestors

import shutil
from datetime import timedelta
from io import StringIO

from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.utils import timezone

from django_tenants.utils import tenant_context

from attachments.models import Attachment
from tcms.tests.factories import TestCaseFactory

from tcms_tenants.storage import TenantFileSystemStorage
from tcms_tenants.tests import TenantGroupsTestCase, tenants_with_schema


class RemoveAttachmentsOlderThanTestCase(TenantGroupsTestCase):
    storage = TenantFileSystemStorage()

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

            self.addCleanup(
                shutil.rmtree,
                self.storage.path(f"attachments/testcases_testcase/{parent_obj.pk}"),
                True,
            )

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
                self.assertFalse(self.storage.exists(old.attachment_file.name))
                self.assertTrue(self.storage.exists(new.attachment_file.name))

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
                    self.assertTrue(
                        self.storage.exists(
                            seeded[tenant.schema_name].attachment_file.name
                        )
                    )
