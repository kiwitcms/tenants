# Copyright (c) 2026 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

from django.core.management.base import BaseCommand
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

    def handle(self, *args, **kwargs):
        answer = kwargs["answer"]

        output = None
        if kwargs["verbosity"]:
            output = self.stdout

        for tenant in get_tenant_model().objects.all():
            if output:
                output.write(
                    f"\n\n === Removing attachments for tenant '{tenant.schema_name}' ==="
                )

            with tenant_context(tenant):
                for attachment in Attachment.objects.all():
                    if not attachment.object_id or attachment.content_object is None:
                        if output:
                            output.write(
                                f"Attachment `{attachment}' to non-existing "
                                f"`{attachment.content_type.model}' with PK "
                                f"`{attachment.object_id}'"
                            )

                        while answer not in "yn":
                            answer = input("Do you wish to delete? [yN] ")
                            if not answer:
                                answer = "x"
                                continue
                            answer = answer[0].lower()

                        if answer == "y":
                            remove_file_from_disk(attachment.attachment_file)
                            attachment.delete()

                            if output:
                                output.write(f"Deleted attachment `{attachment}'")

            if output:
                output.write(
                    f"\n\n === End removing attachments for tenant '{tenant.schema_name}' ==="
                )
