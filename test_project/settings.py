# pylint: disable=wildcard-import, unused-wildcard-import
# Copyright (c) 2019-2020 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt
# pylint: disable=invalid-name, protected-access, wrong-import-position
import os
import sys
import pkg_resources

# pretend this is a plugin during testing & development
# IT NEEDS TO BE BEFORE the wildcard import below !!!
# .egg-info/ directory will mess up with this
dist = pkg_resources.Distribution(__file__)
entry_point = pkg_resources.EntryPoint.parse('kiwitcms_tenants_devel = tcms_tenants',
                                             dist=dist)
dist._ep_map = {'kiwitcms.plugins': {'kiwitcms_tenants_devel': entry_point}}
pkg_resources.working_set.add(dist)

from tcms.settings.product import *  # noqa: F403

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, BASE_DIR)

# check for a clean devel environment
if os.path.exists(os.path.join(BASE_DIR, "kiwitcms_tenants.egg-info")):
    print("ERORR: .egg-info/ directories mess up plugin loading code in devel mode")
    sys.exit(1)

# import the settings which automatically get distributed with this package
multi_tenant_settings = os.path.join(
    BASE_DIR, 'tcms_settings_dir', 'multi_tenant.py')

# Kiwi TCMS loads extra settings in the same way using exec()
exec(  # pylint: disable=exec-used
    open(multi_tenant_settings, "rb").read(),
    globals()
)


# these are enabled only for testing purposes
DEBUG = True
TEMPLATE_DEBUG = True
MEDIA_ROOT = os.path.join(BASE_DIR, 'uploads')
LOCALE_PATHS = [os.path.join(BASE_DIR, 'tcms_tenants', 'locale')]


# start multi-tenant settings override
DATABASES['default'].update({  # noqa: F405 pylint: disable=objects-update-used
    'NAME': 'test_project',
    'USER': 'kiwi',
    'PASSWORD': 'kiwi',
    'HOST': 'localhost',
    'OPTIONS': {},
})
