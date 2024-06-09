# Copyright (c) 2019 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tcms_tenants", "0003_use_datetime_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenant",
            name="organization",
            field=models.CharField(blank=True, db_index=True, max_length=64, null=True),
        ),
    ]
