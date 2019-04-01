.PHONY: messages
messages:
	./manage.py makemessages --no-obsolete --no-vinaigrette --ignore "test*.py"
	ls tcms_tenants/locale/*/LC_MESSAGES/*.po | xargs -n 1 -I @ msgattrib -o @ --no-fuzzy @


.PHONY: test
test:
	EXECUTOR=standard PYTHONWARNINGS=d \
	coverage run --source='tcms_tenants' ./manage.py test tcms_tenants.tests


.PHONY: check
check: test
