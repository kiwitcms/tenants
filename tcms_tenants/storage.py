# Copyright (c) 2019-2020 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

import os

from django.conf import settings
from django.utils.functional import cached_property
from django.core.files.storage import FileSystemStorage

from django_tenants import utils


class TenantFileSystemStorage(FileSystemStorage):
    """
    Implementation that extends core Django's FileSystemStorage for multi-tenant setups,
    storing files under induvidual directories. Workaround until
    https://github.com/tomturner/django-tenants/pull/252 gets merged.
    """

    @cached_property
    def relative_media_root(self):  # pylint: disable=no-self-use
        return getattr(settings, "MULTITENANT_RELATIVE_MEDIA_ROOT", "%s")

    @property  # not cached like in parent class
    def base_url(self):  # pylint: disable=invalid-overridden-method
        _url = super().base_url
        _url = os.path.join(
            _url, utils.parse_tenant_config_path(self.relative_media_root)
        )
        if not _url.endswith("/"):
            _url += "/"
        return _url

    @property  # not cached like in parent class
    def location(self):  # pylint: disable=invalid-overridden-method
        _location = os.path.join(
            super().location, utils.parse_tenant_config_path(self.relative_media_root)
        )
        return os.path.abspath(_location)
