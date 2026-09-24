# Copyright (c) 2026 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.utils import timezone
from django_tenants.utils import get_tenant_model, tenant_context

from attachments.models import Attachment
from attachments.views import remove_file_from_disk


class Command(BaseCommand):
    help = (
        "Remove attachments for which the related objects don't exist anymore! "
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
        parser.add_argument(
            "--check-storage",
            action="store_true",
            default=False,
            help="Also remove attachments whose file is missing from storage",
        )

    @staticmethod
    def prompt_and_remove(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        attachment, message, output, dry_run, answer, delete_file=True
    ):
        if output:
            output.write(message)

        if dry_run:
            return

        while answer not in "yn":
            answer = input("Do you wish to delete? [yN] ")
            if not answer:
                answer = "x"
                continue
            answer = answer[0].lower()

        if answer == "y":
            if delete_file:
                remove_file_from_disk(attachment.attachment_file)
            attachment.delete()

            if output:
                output.write(f"Deleted attachment `{attachment}'")

    def handle(self, *args, **kwargs):
        answer = kwargs["answer"]
        dry_run = kwargs["dry_run"]
        check_storage = kwargs["check_storage"]

        output = None
        if kwargs["verbosity"]:
            output = self.stdout

        for tenant in get_tenant_model().objects.all():
            if output:
                output.write(
                    f"\n\n {timezone.now()} === Removing attachments"
                    f" for tenant '{tenant.schema_name}' === dry run: {dry_run} ==="
                )

            with tenant_context(tenant):
                for attachment in Attachment.objects.all():
                    if not attachment.object_id or attachment.content_object is None:
                        self.prompt_and_remove(
                            attachment,
                            f"Attachment `{attachment}' to non-existing "
                            f"`{attachment.content_type.model}' with PK "
                            f"`{attachment.object_id}'",
                            output,
                            dry_run,
                            answer,
                        )
                    elif check_storage and not default_storage.exists(
                        attachment.attachment_file.name
                    ):
                        self.prompt_and_remove(
                            attachment,
                            f"Attachment `{attachment}' with missing file",
                            output,
                            dry_run,
                            answer,
                            delete_file=False,
                        )

            if output:
                output.write(
                    f"\n\n {timezone.now()} === End removing attachments"
                    f" for tenant '{tenant.schema_name}' ==="
                )
