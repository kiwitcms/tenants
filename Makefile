.PHONY: messages
messages:
	./manage.py makemessages --no-obsolete --no-vinaigrette --ignore "test*.py"
	ls tcms_tenants/locale/*/LC_MESSAGES/*.po | xargs -n 1 -I @ msgattrib -o @ --no-fuzzy @


.PHONY: test
test:
	EXECUTOR=standard PYTHONWARNINGS=d \
	    coverage run --include "tcms_tenants/*.py" \
	                 --omit "tcms_tenants/tests/*.py" \
	                 ./manage.py test -v2 tcms_tenants.tests


.PHONY: pylint
pylint:
	pylint --load-plugins=pylint_django -d missing-docstring -d duplicate-code \
	    -d wildcard-import -d unused-wildcard-import *.py tcms_tenants/ test_project/

.PHONY: check
check: pylint test
