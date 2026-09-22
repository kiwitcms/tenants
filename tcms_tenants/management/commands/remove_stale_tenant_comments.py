# Copyright (c) 2026 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db.models import TextField
from django.db.models.functions import Cast
from django_tenants.utils import get_tenant_model, tenant_context
from django_comments.models import Comment


class Command(BaseCommand):
    help = (
        "Remove comments for which the related objects don't exist anymore! "
        "Works on all tenants!"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "-y",
            "--yes",
            default="x",
            action="store_const",
            const="y",
            dest="answer",
            help="Automatically confirm deletion",
        )

    def handle(self, *args, **kwargs):
        answer = kwargs["answer"]

        output = None
        if kwargs["verbosity"]:
            output = self.stdout

        for tenant in get_tenant_model().objects.all():
            if output:
                output.write(
                    f"\n\n === Removing comments for tenant '{tenant.schema_name}' ==="
                )

            with tenant_context(tenant):
                stale_comments = Comment.objects.all()

                for content_type_id in Comment.objects.values_list(
                    "content_type", flat=True
                ).distinct():
                    content_type = ContentType.objects.get_for_id(content_type_id)
                    model = content_type.model_class()
                    if model is None:
                        continue

                    stale_comments = stale_comments.exclude(
                        content_type_id=content_type_id,
                        object_pk__in=model.objects.annotate(
                            pk_as_text=Cast("pk", TextField())
                        ).values("pk_as_text"),
                    )

                for comment in stale_comments:
                    if output:
                        output.write(
                            f"Comment `{comment}' to non-existing "
                            f"`{comment.content_type.model}' with PK "
                            f"`{comment.object_pk}'"
                        )

                    while answer not in "yn":
                        answer = input("Do you wish to delete? [yN] ")
                        if not answer:
                            answer = "x"
                            continue
                        answer = answer[0].lower()

                    if answer == "y":
                        comment.delete()

                        if output:
                            output.write(f"Deleted comment `{comment}'")

            if output:
                output.write(
                    f"\n\n === End removing comments for tenant '{tenant.schema_name}' ==="
                )
