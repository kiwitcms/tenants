# Copyright (c) 2024 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt

import datetime

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Initialize tenants for a *NEW* Kiwi TCMS Enterprise installation."

    def add_arguments(self, parser):
        parser.add_argument(
            "--domain",
            action="store",
            dest="domain",
            required=True,
            help="The primary tenant domain",
        )

    def handle(self, *args, **kwargs):
        superuser = get_user_model().objects.filter(is_superuser=True).first()
        paid_until = timezone.now() + datetime.timedelta(days=100 * 365)
        domain = kwargs["domain"]

        call_command(
            "create_tenant",
            f"--verbosity={kwargs['verbosity']}",
            "--schema_name",
            "public",
            "--name",
            "Public tenant",
            "--paid_until",
            paid_until.isoformat(),
            "--publicly_readable",
            False,
            "--owner_id",
            superuser.pk,
            "--organization",
            "Testing department",
            "--domain-domain",
            domain,
            "--domain-is_primary",
            True,
        )

        # a special tenant to make cloning faster
        call_command(
            "create_tenant",
            f"--verbosity={kwargs['verbosity']}",
            "--schema_name",
            "empty",
            "--name",
            "Cloning Template",
            "--paid_until",
            paid_until.isoformat(),
            "--publicly_readable",
            False,
            "--owner_id",
            superuser.pk,
            "--organization",
            "Kiwi TCMS",
            "--domain-domain",
            "empty.example.org",
            "--domain-is_primary",
            True,
        )
