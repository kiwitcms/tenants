# Copyright (c) 2026 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

from django.core.files.storage import default_storage
from django.utils import timezone
from django_tenants.utils import get_tenant_model, tenant_context

from attachments.management.commands.delete_stale_attachments import (
    Command as DeleteStaleAttachmentsCommand,
)
from attachments.models import Attachment
from attachments.views import remove_file_from_disk


class Command(DeleteStaleAttachmentsCommand):
    help = (
        "Remove attachments for which the related objects don't exist anymore! "
        "Works on all tenants!"
    )

    def add_arguments(self, parser):
        super().add_arguments(parser)
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

        if dry_run:
            # the upstream command reports each match before prompting, so
            # refusing to delete turns it into a dry run
            kwargs["answer"] = "n"

        for tenant in get_tenant_model().objects.all():
            if output:
                output.write(
                    f"\n\n {timezone.now()} === Removing attachments"
                    f" for tenant '{tenant.schema_name}' === dry run: {dry_run} ==="
                )

            with tenant_context(tenant):
                # upstream removes attachments whose related object is gone
                super().handle(*args, **kwargs)

                if check_storage:
                    for attachment in Attachment.objects.all():
                        if attachment.content_object and not (
                            default_storage.exists(attachment.attachment_file.name)
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
