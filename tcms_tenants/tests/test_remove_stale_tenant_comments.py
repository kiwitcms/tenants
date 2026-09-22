# Copyright (c) 2026 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

# pylint: disable=too-many-ancestors

from io import StringIO

from django.core.management import call_command
from django.db.models import IntegerField
from django.db.models.functions import Cast

from django_tenants.utils import (
    get_tenant_model,
    schema_exists,
    tenant_context,
)
from django_comments.models import Comment

from tcms.core.helpers.comments import add_comment
from tcms.tests.factories import TestCaseFactory, TestExecutionFactory, TestPlanFactory

from tcms_tenants.tests import TenantGroupsTestCase


class RemoveStaleTenantCommentsTestCase(TenantGroupsTestCase):
    comments_per_model = 100
    pk_offset = 1_000_000_000

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
                for _ in range(cls.comments_per_model):
                    cls.add_comments(TestCaseFactory)
                    cls.add_comments(TestExecutionFactory)
                    cls.add_comments(TestPlanFactory)

    @classmethod
    def add_comments(cls, factory_class):
        obj = factory_class()

        _ = add_comment([obj], "comment on a existing object", self.tester)[0]

        stale = add_comment([obj], "comment on a deleted object", self.tester)[0]
        stale.object_pk = str(int(obj.pk) + cls.pk_offset)
        stale.save()

        stale2 = add_comment([obj], "comment with object_pk=''", self.tenant.owner)[0]
        stale2.object_pk = ""
        stale2.save()

    def test_removes_only_comments_which_are_attached_to_missing_objects(self):
        tenants = self.tenants_with_schema()
        self.assertGreaterEqual(len(tenants), 1)

        for tenant in tenants:
            with tenant_context(tenant):
                self.assertTrue(
                    Comment.objects.exclude(object_pk="")
                    .annotate(object_pk_as_int=Cast("object_pk", IntegerField()))
                    .filter(object_pk_as_int__gt=self.pk_offset)
                    .exists()
                )
                self.assertEqual(
                    Comment.objects.count(), self.comments_per_model * 3 * 3
                )

        out = StringIO()
        call_command(
            "remove_stale_tenant_comments",
            answer="y",
            verbosity=1,
            stdout=out,
        )

        output = out.getvalue()

        for tenant in tenants:
            with tenant_context(tenant):
                self.assertEqual(Comment.objects.count(), self.comments_per_model * 3)
                self.assertFalse(
                    Comment.objects.exclude(object_pk="")
                    .annotate(object_pk_as_int=Cast("object_pk", IntegerField()))
                    .filter(object_pk_as_int__gt=self.pk_offset)
                    .exists()
                )

            for banner in ("Removing comments", "End removing comments"):
                self.assertIn(
                    f"=== {banner} for tenant '{tenant.schema_name}' ===",
                    output,
                )
