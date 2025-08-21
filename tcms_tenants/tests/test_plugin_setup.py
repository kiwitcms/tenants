# Copyright (c) 2020-2025 Alexander Todorov <atodorov@otb.bg>
#
# Licensed under GNU Affero General Public License v3 or later (AGPLv3+)
# https://www.gnu.org/licenses/agpl-3.0.html

# pylint: disable=too-many-ancestors

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from tcms_tenants import menu
from tcms_tenants.tests import LoggedInTestCase


class PluginSetupTestCase(LoggedInTestCase):
    def test_installed_apps_contains_tcms_tenants(self):
        self.assertIn("tcms_tenants", settings.INSTALLED_APPS)

    def test_menu_is_updated(self):
        for name, target in settings.MENU_ITEMS:
            if name == _("MORE"):
                for menu_item in menu.MENU_ITEMS:
                    self.assertIn(menu_item, target)

                return

        self.fail("MORE not found in settings.MENU_ITEMS")

    def test_menu_rendering(self):
        response = self.client.get("/", follow=True)
        self.assertContains(response, "Tenant")
        self.assertContains(response, "Authorized users")
