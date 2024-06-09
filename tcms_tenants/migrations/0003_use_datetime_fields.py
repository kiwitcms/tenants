# Copyright (c) 2019 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tcms_tenants", "0002_tenant_owner"),
    ]

    operations = [
        migrations.AlterField(
            model_name="tenant",
            name="created_on",
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        migrations.AlterField(
            model_name="tenant",
            name="paid_until",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
    ]
