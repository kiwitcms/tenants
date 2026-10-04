# Copyright (c) 2026 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

from django.utils import timezone
from django_tenants.utils import get_tenant_model, tenant_context
from simple_history.management.commands.populate_history import (
    Command as PopulateHistoryCommand,
)


class Command(PopulateHistoryCommand):
    help = (
        "Populates the corresponding HistoricalRecords field with "
        "the current state of all instances in a model for all tenants"
    )

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Don't create anything, just report what would be populated",
        )

    def handle(  # pylint: disable=attribute-defined-outside-init
        self, *args, **options
    ):
        self.verbosity = options["verbosity"]
        self.dry_run = options["dry_run"]

        output = None
        if self.verbosity:
            output = self.stdout

        for tenant in get_tenant_model().objects.all():
            if output:
                output.write(
                    f"\n\n {timezone.now()} === Populating history"
                    f" for tenant '{tenant.schema_name}' === dry run: {self.dry_run} ==="
                )

            with tenant_context(tenant):
                super().handle(*args, **options)

            if output:
                output.write(
                    f"\n\n {timezone.now()} === End populating history"
                    f" for tenant '{tenant.schema_name}' ==="
                )

    def _bulk_history_create(self, model, batch_size):
        if self.dry_run:
            return

        super()._bulk_history_create(model, batch_size)
