# Copyright (c) 2025 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

# pylint: disable=missing-permission-required, no-self-use

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.forms.models import model_to_dict
from modernrpc.core import rpc_method

from tcms.rpc.decorators import permissions_required
from tenant_groups.forms import GroupForm
from tenant_groups.models import Group


@permissions_required("tenant_groups.view_group")
@rpc_method(name="TenantGroup.filter")
def filter(query):  # pylint: disable=redefined-builtin
    """
    .. function:: RPC TenantGroup.filter(query)

        Search and return the resulting list of tenant groups.

        :param query: Field lookups for :class:`tenant_groups.models.Group`
        :type query: dict
        :return: Serialized list of :class:`tenant_groups.models.Group` objects
        :rtype: list(dict)
        :raises PermissionDenied: if missing the *tenant_groups.view_group* permission

    .. versionadded:: 15.3
    """
    return list(
        Group.objects.filter(**query)
        .values(
            "id",
            "name",
        )
        .distinct()
    )


@permissions_required("tenant_groups.change_group")
@rpc_method(name="TenantGroup.add_permission")
def add_permission(group_id, perm):
    """
    .. function:: RPC TenantGroup.add_permission(group_id, permission_label)

        Add the specified permission label to a tenant group.

        :param group_id: PK for a :class:`tenant_groups.models.Group` object
        :type group_id: int
        :param perm: A permission label string
        :type perm: str
        :raises PermissionDenied: if missing the *tenant_groups.change_group* permission
        :raises DoesNotExist: if group doesn't exist
        :raises ValueError: if permission label is invalid

    .. versionadded:: 15.3
    """
    group = Group.objects.get(pk=group_id)

    try:
        app_label, codename = perm.split(".")
    except ValueError:
        raise ValueError(f'"{perm}" should be: app_label.perm_codename') from None

    if not app_label or not codename:
        raise ValueError("Invalid app_label or codename")

    group.permissions.add(
        Permission.objects.get(content_type__app_label=app_label, codename=codename)
    )


@permissions_required("tenant_groups.change_group")
@rpc_method(name="TenantGroup.add_user")
def add_user(group_id, user_id):
    """
    .. function:: RPC TenantGroup.add_user(group_id, user_id)

        Add the specified user to a tenant group.

        :param group_id: PK for a :class:`tenant_groups.models.Group` object
        :type group_id: int
        :param user_id: PK for a :class:`django.contrib.auth.models.User` object
        :type user_id: int
        :raises PermissionDenied: if missing the *tenant_groups.change_group* permission
        :raises DoesNotExist: if group or user doesn't exist

    .. versionadded:: 15.3
    """
    group = Group.objects.get(pk=group_id)
    user = get_user_model().objects.get(pk=user_id)

    group.user_set.add(user)


@rpc_method(name="TenantGroup.create")
@permissions_required("tenant_groups.add_group")
def create(values):
    """
    .. function:: RPC TenantGroup.create(values)

        Create a new tenant Group object and store it in the database.

        :param values: Field values for :class:`tenant_groups.models.Group`
        :type values: dict
        :return: Serialized :class:`tenant_groups.models.Group` object
        :rtype: dict
        :raises ValueError: if input values don't validate
        :raises PermissionDenied: if missing *tenant_groups.add_group* permission

    .. versionadded:: 15.3
    """
    form = GroupForm(values)

    if form.is_valid():
        group = form.save()
        return model_to_dict(group)

    raise ValueError(list(form.errors.items()))
