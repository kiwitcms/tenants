# Copyright (c) 2019 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt

from django.db import models, migrations
import django_tenants.postgresql_backend.base


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Tenant',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('schema_name', models.CharField(unique=True, max_length=63, db_index=True,
                                                 validators=[django_tenants.postgresql_backend.base._check_schema_name])),
                ('name', models.CharField(max_length=100, db_index=True)),
                ('created_on', models.DateField(auto_now_add=True)),
                ('paid_until', models.DateField(null=True, blank=True)),
                ('on_trial', models.BooleanField(default=False)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Domain',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('domain', models.CharField(unique=True, max_length=253, db_index=True)),
                ('is_primary', models.BooleanField(default=True, db_index=True)),
                ('tenant', models.ForeignKey(related_name='domains', to='tcms_tenants.Tenant', on_delete=models.deletion.CASCADE)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
