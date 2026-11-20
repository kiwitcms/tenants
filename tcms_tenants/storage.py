# Copyright (c) 2019-2026 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

import os
import shutil

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from storages.backends.s3 import S3Storage
from storages.utils import safe_join as storage_safe_join

from django_tenants import utils


class TenantFileSystemStorage(FileSystemStorage):
    """
    Implementation that extends core Django's FileSystemStorage for multi-tenant setups,
    storing files under induvidual directories. Workaround until
    https://github.com/tomturner/django-tenants/pull/252 gets merged.
    """

    @property  # not cached like in parent class
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

    def delete_recursively(self, path):
        if self.exists(path):
            shutil.rmtree(path)


class TenantS3Storage(S3Storage):  # pylint: disable=abstract-method
    def __init__(self, **kwargs):
        self._location = kwargs.get("location")
        if self._location is None:
            self._location = self.get_default_settings()["location"]

        super().__init__(**kwargs)

    @property
    def location(self):
        relative_media_root = getattr(settings, "MULTITENANT_RELATIVE_MEDIA_ROOT", "%s")
        return os.path.join(
            self._location,
            utils.parse_tenant_config_path(relative_media_root),
        )

    def path(self, name):
        """
        Return the object's S3 key. Unlike a filesystem path it doesn't
        start with a slash.
        """
        return storage_safe_join(self.location, name)

    def delete_recursively(self, path):
        prefix = path.rstrip("/") + "/"
        for obj in self.bucket.objects.filter(Prefix=prefix):
            obj.delete()
