Multi-tenant support for Kiwi TCMS
==================================

.. image:: https://travis-ci.org/kiwitcms/tenants.svg?branch=master
    :target: https://travis-ci.org/kiwitcms/tenants

.. image:: https://coveralls.io/repos/github/kiwitcms/tenants/badge.svg?branch=master
   :target: https://coveralls.io/github/kiwitcms/tenants?branch=master

.. image:: https://pyup.io/repos/github/kiwitcms/tenants/shield.svg
    :target: https://pyup.io/repos/github/kiwitcms/tenants/
    :alt: Python updates

.. image:: https://d322cqt584bo4o.cloudfront.net/kiwitcms-tenants/localized.svg
   :target: https://crowdin.com/project/kiwitcms-tenants
   :alt: Translate

.. image:: https://opencollective.com/kiwitcms/tiers/sponsor/badge.svg?label=sponsors&color=brightgreen
   :target: https://opencollective.com/kiwitcms#contributors
   :alt: Become a sponsor


Introduction
------------

This package provides multi-tenant support for Kiwi TCMS and is a wrapper
around `django-tenants <https://github.com/tomturner/django-tenants>`_.
You can use it to host different organizations on the same application server or host
multiple product instances used by different teams. Each tenant is able to see
only the information created by themselves.

To install::

    pip install kiwitcms-tenants

Then see
`test_project/settings.py <https://github.com/kiwitcms/tenants/blob/master/test_project/settings.py>`_
for more information about configuration options.

IMPORTANT: multi-tenancy is backed by PostgreSQL schemas!

WARNING: current tenant is decided based on the FQDN by which you
are accessing Kiwi TCMS. This means your web server and DNS must support
wildcard domains, e.g. ``*.tenants.kiwitcms.org``. How to configure them
is not currently documented here!

Changelog
---------


v0.4.0 (12 May 2019)
~~~~~~~~~~~~~~~~~~~~

- Allow overriding create tenant form URL via additional
  context variable named ``form_action_url``


v0.3.0 (08 May 2019)
~~~~~~~~~~~~~~~~~~~~

- Send email when a new tenant is created
- Add middleware which can be used to block unpaid tenants
- Rewrite middleware without deprecated ``MiddlewareMixin``, Refers to
  `Issue #17 <https://github.com/kiwitcms/tenants/issues/17>`_
- Add more tests

v0.2.0 (05 May 2019)
~~~~~~~~~~~~~~~~~~~~

- Remove ``django.contrib.contenttypes`` from ``TENANT_APPS``
- Make it easier to override ``NewTenantView``
- Use ``DateTimeField`` instead of ``DateField``
- Show first primary domain in Admin
- Massive speed up tests
- Pylint fixes


v0.1.10 (03 May 2019)
~~~~~~~~~~~~~~~~~~~~~

- Bring back ``tenant_url`` template tag with optional
  ``schema_name`` parameter


v0.1.9 (03 May 2019)
~~~~~~~~~~~~~~~~~~~~

- Fix failing tests


v0.1.8 (03 May 2019)
~~~~~~~~~~~~~~~~~~~~

- Fix packaging for missing migrations directory
- Add view which facilitates GitHub login & redirects.
  Callers are supposed to perform OAuth login via public tenant and then
  redirect to this view which will send the browser to the actual tenant!
  This will resolve problems with ``redirect_uri`` mismatch that we're
  seeing from GitHub b/c you can only specify one redirect uri
- pylint fixes
- Remove unused ``templatetags/`` directory


v0.1.6 (28 April 2019)
~~~~~~~~~~~~~~~~~~~~~~

- Tenant object now has an owner


v0.1.5 (24 April 2019)
~~~~~~~~~~~~~~~~~~~~~~

- Update django-tenants to 2.2.3
- New translations for Slovenian
- Don't ship ``test_project/`` files in wheel package


v0.1.4 (15 April 2019)
~~~~~~~~~~~~~~~~~~~~~~

- Update to django-tenants 2.2.0 for Django 2.2 support


v0.1.3 (10 April 2019)
~~~~~~~~~~~~~~~~~~~~~~

- Rename setting ``TCMS_TENANTS_DOMAIN`` to ``KIWI_TENANTS_DOMAIN``


v0.1.2 (04 April 2019) - initial release
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Support creating of tenants via web interface
- Support for deleting tenants only by super-user
- Support for authorizing other users to access the current tenant
- Middleware which returns 403 Forbidden when non-authorized user
  tries to access a tenant
- Support for overriding the ``tcms_tenants/new.html`` template to
  provide SLA, terms and conditions, etc.
