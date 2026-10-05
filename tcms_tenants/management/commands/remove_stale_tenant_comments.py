# Copyright (c) 2026 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

from django.utils import timezone
from django_tenants.utils import get_tenant_model, tenant_context

from django_comments.management.commands.delete_stale_comments import (
    Command as DeleteStaleCommentsCommand,
)


class Command(DeleteStaleCommentsCommand):
    help = (
        "Remove comments for which the related objects don't exist anymore! "
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

    def handle(self, *args, **kwargs):
        dry_run = kwargs["dry_run"]

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
                    f"\n\n {timezone.now()} === Removing comments"
                    f" for tenant '{tenant.schema_name}' === dry run: {dry_run} ==="
                )

            with tenant_context(tenant):
                # upstream removes comments whose related object is gone
                super().handle(*args, **kwargs)

            if output:
                output.write(
                    f"\n\n {timezone.now()} === End removing comments"
                    f" for tenant '{tenant.schema_name}' ==="
                )
