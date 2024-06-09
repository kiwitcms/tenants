# Copyright (c) 2019-2020 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

from django.conf import settings
from django.db import models, migrations
import django_tenants.postgresql_backend.base


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Tenant",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                (
                    "schema_name",
                    models.CharField(
                        unique=True,
                        max_length=63,
                        db_index=True,
                        validators=[
                            django_tenants.postgresql_backend.base._check_schema_name
                        ],
                    ),
                ),
                ("name", models.CharField(max_length=100, db_index=True)),
                ("created_on", models.DateField(auto_now_add=True, db_index=True)),
                ("paid_until", models.DateField(null=True, blank=True, db_index=True)),
                ("on_trial", models.BooleanField(default=True, db_index=True)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.AddField(
            model_name="tenant",
            name="authorized_users",
            field=models.ManyToManyField(to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name="Domain",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                (
                    "domain",
                    models.CharField(unique=True, max_length=253, db_index=True),
                ),
                ("is_primary", models.BooleanField(default=True, db_index=True)),
                (
                    "tenant",
                    models.ForeignKey(
                        related_name="domains",
                        to="tcms_tenants.Tenant",
                        on_delete=models.deletion.CASCADE,
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
