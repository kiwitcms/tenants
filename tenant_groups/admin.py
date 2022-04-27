# Copyright (c) 2022 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt


from django import forms
from django.contrib import admin
from django.contrib import auth
from django.utils.text import capfirst
from django.utils.translation import gettext_lazy as _

from tcms_tenants.utils import get_current_tenant
from tenant_groups.models import Group


class GroupAdminForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ["name", "permissions"]

    users = forms.ModelMultipleChoiceField(
        queryset=auth.get_user_model().objects.none(),
        required=False,
        widget=admin.widgets.FilteredSelectMultiple("users", False),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["users"].label = capfirst(_("users"))
        self.fields["users"].queryset = get_current_tenant().authorized_users.all()
        if self.instance.pk:
            self.fields["users"].initial = self.instance.user_set.all()

        if "permissions" in self.fields:
            self.fields["permissions"].queryset = auth.models.Permission.objects.filter(
                content_type__app_label__in=Group.relevant_apps
            )
            if self.instance.pk:
                self.fields["permissions"].initial = self.instance.permissions.all()

    def save(self, commit=True):
        instance = super().save(commit=commit)
        instance.save()

        self.instance.user_set.set(self.cleaned_data["users"])
        self.save_m2m()

        return instance


class GroupAdmin(auth.admin.GroupAdmin):
    form = GroupAdminForm

    def has_delete_permission(self, request, obj=None):
        if obj and obj.name in ["Tester", "Administrator"]:
            return False
        return super().has_delete_permission(request, obj)

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj=obj)
        name_index = fields.index("name")

        # make sure Name is always the first field
        if name_index > 0:
            del fields[name_index]
            fields.insert(0, "name")

        return fields

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        if obj and obj.name in ["Tester", "Administrator"]:
            readonly_fields = readonly_fields + ("name",)

        return readonly_fields


admin.site.register(Group, GroupAdmin)
