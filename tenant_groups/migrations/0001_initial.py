# Copyright (c) 2022 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

from django.conf import settings
from django.db import connections
from django.db import migrations, models

from django_tenants.utils import (
    get_public_schema_name,
    get_tenant_database_alias,
)


def forwards_add_default_groups_and_permissions(apps, schema_editor):
    current_tenant = connections[get_tenant_database_alias()].tenant
    if current_tenant.schema_name == get_public_schema_name():
        return

    group_model = apps.get_model("tenant_groups", "Group")
    group_model.objects.bulk_create(
        [
            group_model(name="Administrator"),
            group_model(name="Tester"),
        ]
    )

    permission_model = apps.get_model("auth", "Permission")

    tester = group_model.objects.get(name="Tester")
    tester_perms = tester.permissions.all()
    # apply all permissions for test case & product management
    for app_name in [
        "bugs",
        "django_comments",
        "linkreference",
        "management",
        "testcases",
        "testplans",
        "testruns",
        "attachments",
    ]:
        app_perms = permission_model.objects.filter(
            content_type__app_label__contains=app_name
        )
        app_perms = app_perms.exclude(pk__in=tester_perms).exclude(
            content_type__app_label="attachments",
            codename="delete_foreign_attachments",
        )
        tester.permissions.add(*app_perms)

    # Admin gets the same permissions as Tester + tenant_groups
    admin = group_model.objects.get(name="Administrator")
    admin.permissions.add(*tester.permissions.all())
    admin.permissions.add(
        *permission_model.objects.filter(content_type__app_label="tenant_groups")
    )


def forwards_add_authorized_users_to_default_groups(apps, schema_editor):
    current_tenant = connections[get_tenant_database_alias()].tenant
    if current_tenant.schema_name in [get_public_schema_name(), "empty"]:
        return

    group_model = apps.get_model("tenant_groups", "Group")
    tenant_model = apps.get_model("tcms_tenants", "Tenant")

    tester = group_model.objects.get(name="Tester")
    administrator = group_model.objects.get(name="Administrator")

    # Replace FakeTenant with Tenant b/c we need to access .owner
    current_tenant = tenant_model.objects.get(schema_name=current_tenant.schema_name)

    # make sure that existing users are assigned to default groups
    # to preserve older behavior
    administrator.user_set.add(current_tenant.owner)
    tester.user_set.add(*current_tenant.authorized_users.all())


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("tcms_tenants", "0005_rename_on_trial_to_public_read"),
    ]

    operations = [
        migrations.CreateModel(
            name="Group",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(max_length=150, unique=True, verbose_name="name"),
                ),
                (
                    "permissions",
                    models.ManyToManyField(
                        blank=True,
                        related_name="tenant_groups",
                        to="auth.Permission",
                        verbose_name="permissions",
                    ),
                ),
                (
                    "user_set",
                    models.ManyToManyField(
                        to=settings.AUTH_USER_MODEL, related_name="tenant_groups"
                    ),
                ),
            ],
            options={
                "verbose_name": "group",
                "verbose_name_plural": "groups",
            },
        ),
        migrations.RunPython(
            code=forwards_add_default_groups_and_permissions,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RunPython(
            code=forwards_add_authorized_users_to_default_groups,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
