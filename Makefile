.PHONY: messages
messages:
	./manage.py makemessages --no-obsolete --no-vinaigrette --ignore "test*.py"
	ls tcms_tenants/locale/*/LC_MESSAGES/*.po | xargs -n 1 -I @ msgattrib -o @ --no-fuzzy @


.PHONY: test
test:
	EXECUTOR=standard PYTHONWARNINGS=d AUTO_CREATE_SCHEMA='' \
	    coverage run --include "tcms_tenants/*.py" \
	                 --omit "tcms_tenants/tests/*.py" \
	                 ./manage.py test -v2 tcms_tenants.tests

.PHONY: test_for_missing_migrations
test_for_missing_migrations:
	./manage.py migrate
	./manage.py makemigrations --check

.PHONY: pylint
pylint:
	pylint --load-plugins=pylint_django -d missing-docstring -d duplicate-code \
	    -d wildcard-import -d unused-wildcard-import *.py tcms_tenants/ test_project/

.PHONY: flake8
flake8:
	flake8 *.py tcms_tenants/ test_project/

.PHONY: check
check: flake8 pylint test_for_missing_migrations test
