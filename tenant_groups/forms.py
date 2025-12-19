# Copyright (c) 2025 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

# pylint: disable=missing-permission-required, no-self-use

from django import forms

from tenant_groups.models import Group


class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        exclude = ("permissions", "user_set")  # pylint: disable=modelform-uses-exclude
