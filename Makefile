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

KIWI_LINT_INCLUDE_PATH="../Kiwi/"

.PHONY: pylint
pylint:
	if [ ! -d "$(KIWI_LINT_INCLUDE_PATH)/kiwi_lint" ]; then \
	    git clone --depth 1 https://github.com/kiwitcms/Kiwi.git $(KIWI_LINT_INCLUDE_PATH); \
	fi
	
	PYTHONPATH=.:$(KIWI_LINT_INCLUDE_PATH) DJANGO_SETTINGS_MODULE="test_project.settings" \
	pylint --load-plugins=pylint_django --load-plugins=kiwi_lint \
	    -d missing-docstring -d duplicate-code -d module-in-directory-without-init \
	    *.py tcms_settings_dir/ tcms_tenants/ test_project/

.PHONY: flake8
flake8:
	flake8 *.py tcms_settings_dir/ tcms_tenants/ test_project/

.PHONY: check
check: flake8 pylint test_for_missing_migrations test
