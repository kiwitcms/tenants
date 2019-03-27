#!/bin/bash

set -e

DATABASE=${DATABASE_HOST:-localhost}
echo "Database: $DATABASE"

pushd tenant_test_project

for executor in standard multiprocessing; do
    EXECUTOR=$executor python -Wd manage.py test django_tenants.tests
done

popd
