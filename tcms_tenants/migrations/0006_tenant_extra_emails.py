# Copyright (c) 2024 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tcms_tenants", "0005_rename_on_trial_to_public_read"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenant",
            name="extra_emails",
            field=models.CharField(
                blank=True, db_index=True, max_length=256, null=True
            ),
        ),
    ]
