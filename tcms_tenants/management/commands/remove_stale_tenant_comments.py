# Copyright (c) 2026 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

from django.core.management.base import BaseCommand
from django.utils import timezone
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
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Don't remove anything, just report what would be removed",
        )

    def handle(self, *args, **kwargs):
        answer = kwargs["answer"]
        dry_run = kwargs["dry_run"]

        output = None
        if kwargs["verbosity"]:
            output = self.stdout

        for tenant in get_tenant_model().objects.all():
            if output:
                output.write(
                    f"\n\n {timezone.now()} === Removing comments"
                    f" for tenant '{tenant.schema_name}' === dry run: {dry_run} ==="
                )

            with tenant_context(tenant):
                for comment in Comment.objects.all():
                    if not comment.object_pk or comment.content_object is None:
                        if output:
                            output.write(
                                f"Comment `{comment}' to non-existing "
                                f"`{comment.content_type.model}' with PK "
                                f"`{comment.object_pk}'"
                            )

                        if dry_run:
                            continue

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
                    f"\n\n {timezone.now()} === End removing comments"
                    f" for tenant '{tenant.schema_name}' ==="
                )
