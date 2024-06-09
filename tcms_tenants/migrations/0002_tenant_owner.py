# Copyright (c) 2019 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("tcms_tenants", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenant",
            name="owner",
            field=models.ForeignKey(
                on_delete=models.CASCADE,
                related_name="tenant_owner",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
