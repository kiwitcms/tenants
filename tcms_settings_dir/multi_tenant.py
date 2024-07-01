# Copyright (c) 2020-2024 Alexander Todorov <atodorov@otb.bg>
# Copyright (c) 2022 Ivajlo Karabojkov <karabojkov@kitbg.com>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

# pylint: disable=undefined-variable
import os


# start multi-tenant settings override
DATABASES["default"]["ENGINE"] = "django_tenants.postgresql_backend"  # noqa: F821
DATABASE_ROUTERS = [
    "django_tenants.routers.TenantSyncRouter",
]


# attachments storage
DEFAULT_FILE_STORAGE = "tcms_tenants.storage.TenantFileSystemStorage"
MULTITENANT_RELATIVE_MEDIA_ROOT = "tenant/%s"


# this always needs to be the first app
if "django_tenants" not in INSTALLED_APPS:  # noqa: F821
    INSTALLED_APPS.insert(0, "django_tenants")  # noqa: F821

for app_list in (INSTALLED_APPS, TENANT_APPS):  # noqa: F821
    if "tenant_groups" not in app_list:
        app_list.append("tenant_groups")


KIWI_TENANTS_DOMAIN = os.environ.get("KIWI_TENANTS_DOMAIN")


# TenantMainMiddleware always needs to be first
if (
    "django_tenants.middleware.main.TenantMainMiddleware"
    not in MIDDLEWARE  # noqa: F821
):
    MIDDLEWARE.insert(  # noqa: F821
        0, "django_tenants.middleware.main.TenantMainMiddleware"
    )

if (
    "tcms_tenants.middleware.BlockUnauthorizedUserMiddleware"
    not in MIDDLEWARE  # noqa: F821
):
    MIDDLEWARE.append(  # noqa: F821
        "tcms_tenants.middleware.BlockUnauthorizedUserMiddleware"
    )

# replace ModelBackend with GroupsBackend
if "django.contrib.auth.backends.ModelBackend" in AUTHENTICATION_BACKENDS:  # noqa: F821
    idx = AUTHENTICATION_BACKENDS.index(  # noqa: F821
        "django.contrib.auth.backends.ModelBackend"
    )
    AUTHENTICATION_BACKENDS[idx] = "tenant_groups.backends.GroupsBackend"  # noqa: F821

if (
    "tcms_tenants.backends.PubliclyReadableBackend"
    not in AUTHENTICATION_BACKENDS  # noqa: F821
):
    AUTHENTICATION_BACKENDS.append(  # noqa: F821
        "tcms_tenants.backends.PubliclyReadableBackend"
    )


TENANT_MODEL = "tcms_tenants.Tenant"
TENANT_DOMAIN_MODEL = "tcms_tenants.Domain"


# share login session between tenants
SESSION_COOKIE_DOMAIN = f".{KIWI_TENANTS_DOMAIN}"


# everybody can access the main instance
SHARED_APPS = INSTALLED_APPS  # noqa: F821

# extra context processors
for processor in (
    "tcms_tenants.context_processors.schema_name_processor",
    "tcms_tenants.context_processors.tenant_navbar_processor",
):
    if processor not in TEMPLATES[0]["OPTIONS"]["context_processors"]:  # noqa: F821
        TEMPLATES[0]["OPTIONS"]["context_processors"].append(  # noqa: F821
            processor
        )  # noqa: F821
