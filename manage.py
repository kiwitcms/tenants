#!/usr/bin/env python
# pylint: disable=missing-docstring

import os
import sys

if __name__ == "__main__":
    if os.path.exists("kiwitcms_tenants.egg-info"):
        print("ERORR: .egg-info/ directories mess up plugin loading code in devel mode")
        sys.exit(1)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_project.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
