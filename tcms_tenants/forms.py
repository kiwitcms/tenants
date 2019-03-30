# Copyright (c) 2019 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt

from django import forms
from django_tenants.postgresql_backend import base as validators

from tcms_tenants import utils


class NewTenantForm(forms.Form):
    name = forms.CharField(max_length=100)
    schema_name = forms.CharField(max_length=63,
                                  validators=[validators._check_schema_name,
                                              utils.schema_name_not_used])
