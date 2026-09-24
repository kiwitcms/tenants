# Copyright (c) 2026 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Perform post-upgrade tasks for all tenants"

    def add_arguments(self, parser):
        parser.add_argument(
            "--noinput",
            "--no-input",
            action="store_false",
            dest="interactive",
            help="Automatic mode. Does not require user confirmation",
        )

    def handle(self, *args, **kwargs):
        answer = "y"
        if kwargs["interactive"]:
            answer = "n"

        self.stdout.write("""To finish the upgrade process, the following
management commands will be executed:

refresh_tenant_permissions
remove_stale_tenant_attachments
remove_stale_tenant_comments
            """)

        self.stdout.write("\n1. Refreshing tenant permissions:")
        call_command(
            "refresh_tenant_permissions",
            verbosity=kwargs["verbosity"],
            interactive=kwargs["interactive"],
        )

        self.stdout.write("\n2. Removing stale attachments:")
        call_command(
            "remove_stale_tenant_attachments",
            verbosity=kwargs["verbosity"],
            answer=answer,
        )

        self.stdout.write("\n3. Removing stale comments:")
        call_command(
            "remove_stale_tenant_comments",
            verbosity=kwargs["verbosity"],
            answer=answer,
        )

        self.stdout.write("Done.")
