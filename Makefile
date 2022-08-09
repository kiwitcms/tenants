KIWI_INCLUDE_PATH="../Kiwi/"

.PHONY: messages
messages:
	./manage.py makemessages --locale en --no-obsolete --no-vinaigrette --ignore "test*.py"
	ls tcms_tenants/locale/*/LC_MESSAGES/*.po | xargs -n 1 -I @ msgattrib -o @ --no-fuzzy @


.PHONY: test
test:
	if [ ! -d "$(KIWI_INCLUDE_PATH)/kiwi_lint" ]; then \
	    git clone --depth 1 https://github.com/kiwitcms/Kiwi.git $(KIWI_INCLUDE_PATH); \
	    pip install -U -r $(KIWI_INCLUDE_PATH)/requirements/base.txt; \
	    pip install -U Django==4.1.1; \
	fi

	PYTHONPATH=.:$(KIWI_INCLUDE_PATH) EXECUTOR=standard PYTHONWARNINGS=d AUTO_CREATE_SCHEMA='' \
        KIWI_TENANTS_DOMAIN='test.com' \
	    coverage run --include "*/*.py" \
	                 --omit "*/tests/*.py" \
	                 ./manage.py test -v2

	PYTHONPATH=.:$(KIWI_INCLUDE_PATH) EXECUTOR=standard PYTHONWARNINGS=d AUTO_CREATE_SCHEMA='' \
        KIWI_TENANTS_DOMAIN='' \
	    ./manage.py check 2>&1 | grep "KIWI_TENANTS_DOMAIN environment variable is not set!"

.PHONY: test_for_missing_migrations
test_for_missing_migrations:
	PYTHONPATH=.:$(KIWI_INCLUDE_PATH) KIWI_TENANTS_DOMAIN='test.com' ./manage.py migrate
	PYTHONPATH=.:$(KIWI_INCLUDE_PATH) KIWI_TENANTS_DOMAIN='test.com' ./manage.py makemigrations --check


.PHONY: pylint
pylint:
	if [ ! -d "$(KIWI_INCLUDE_PATH)/kiwi_lint" ]; then \
	    git clone --depth 1 https://github.com/kiwitcms/Kiwi.git $(KIWI_INCLUDE_PATH); \
	    pip install -U -r $(KIWI_INCLUDE_PATH)/requirements/base.txt; \
	    pip install -U Django==4.1.1; \
	fi

	PYTHONPATH=.:$(KIWI_INCLUDE_PATH) pylint \
	    --load-plugins=pylint.extensions.no_self_use \
	    --load-plugins=pylint_django --django-settings-module=test_project.settings \
	    --load-plugins=kiwi_lint -d similar-string \
	    -d missing-docstring -d duplicate-code -d module-in-directory-without-init \
	    --ignore migrations \
	    *.py tcms_settings_dir/ tcms_tenants/ tenant_groups/ test_project/


.PHONY: flake8
flake8:
	flake8 *.py tcms_settings_dir/ tcms_tenants/ tenant_groups/ test_project/


.PHONY: check
check: flake8 pylint test_for_missing_migrations test
