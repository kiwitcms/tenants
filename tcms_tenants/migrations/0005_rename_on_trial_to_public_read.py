# Copyright (c) 2021 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tcms_tenants", "0004_tenant_organization"),
    ]

    operations = [
        migrations.RenameField(
            model_name="tenant",
            old_name="on_trial",
            new_name="publicly_readable",
        ),
        # change the defaults
        migrations.AlterField(
            model_name="tenant",
            name="publicly_readable",
            field=models.BooleanField(default=False, db_index=True),
        ),
    ]
