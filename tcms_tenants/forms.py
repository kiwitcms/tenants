# Copyright (c) 2019-2020 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt
import re

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from django_tenants.postgresql_backend import base as validators

from tcms_tenants import utils


VALIDATION_RE = re.compile(r'^[a-z0-9]{1,63}$')


def _check_domain_name(name):
    """
        Because we use schema_name as sub-domains interchangeably
        we impose additional restriction on input values:
            alpha-numeric, 63 chars max
    """
    if not VALIDATION_RE.match(name):
        raise ValidationError(_('Invalid string'))


class NewTenantForm(forms.Form):  # pylint: disable=must-inherit-from-model-form
    name = forms.CharField(max_length=100)
    schema_name = forms.CharField(max_length=63,
                                  # pylint: disable=protected-access
                                  validators=[validators._check_schema_name,
                                              _check_domain_name,
                                              utils.schema_name_not_used])
    paid_until = forms.DateTimeField(required=False, widget=forms.HiddenInput)
    on_trial = forms.BooleanField(initial=True, required=False,
                                  widget=forms.HiddenInput)
    organization = forms.CharField(max_length=64, required=False,
                                   widget=forms.HiddenInput)


class InviteUsersForm(forms.Form):  # pylint: disable=must-inherit-from-model-form
    number_of_fields = 10

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for i in self.range:
            self.fields["email_%d" % i] = forms.CharField(required=False)

    def clean(self):
        emails = set()

        for i in self.range:
            email = self.cleaned_data["email_%d" % i]
            if email:
                emails.add(email)

        self.cleaned_data["emails"] = emails

    @property
    def range(self):
        return range(self.number_of_fields)
