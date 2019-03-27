#!/bin/bash
# Copyright (c) 2019 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt

set -e

DATABASE=${DATABASE_HOST:-localhost}
echo "Database: $DATABASE"

pushd tenant_test_project

for executor in standard multiprocessing; do
    EXECUTOR=$executor python -Wd manage.py test django_tenants.tests
done

popd
