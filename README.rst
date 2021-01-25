Multi-tenant support for Kiwi TCMS
==================================

.. image:: https://travis-ci.org/kiwitcms/tenants.svg?branch=master
    :target: https://travis-ci.org/kiwitcms/tenants

.. image:: https://coveralls.io/repos/github/kiwitcms/tenants/badge.svg?branch=master
   :target: https://coveralls.io/github/kiwitcms/tenants?branch=master

.. image:: https://pyup.io/repos/github/kiwitcms/tenants/shield.svg
    :target: https://pyup.io/repos/github/kiwitcms/tenants/
    :alt: Python updates

.. image:: https://tidelift.com/badges/package/pypi/kiwitcms-tenants
    :target: https://tidelift.com/subscription/pkg/pypi-kiwitcms-tenants?utm_source=pypi-kiwitcms-tenants&utm_medium=github&utm_campaign=readme
    :alt: Tidelift

.. image:: https://opencollective.com/kiwitcms/tiers/sponsor/badge.svg?label=sponsors&color=brightgreen
   :target: https://opencollective.com/kiwitcms#contributors
   :alt: Become a sponsor

.. image:: https://img.shields.io/twitter/follow/KiwiTCMS.svg
    :target: https://twitter.com/KiwiTCMS
    :alt: Kiwi TCMS on Twitter


Introduction
------------

This package provides multi-tenant support for Kiwi TCMS and is a wrapper
around `django-tenants <https://github.com/tomturner/django-tenants>`_.
You can use it to host different organizations on the same application server or host
multiple product instances used by different teams. Each tenant is able to see
only the information created by themselves.


Installation
------------

**IMPORTANT:** multi-tenancy is backed by PostgreSQL schemas! It will not work
with a different database backend.

**WARNING:** current tenant is decided based on the FQDN by which you
are accessing Kiwi TCMS!

The following changes need to be introduced into a downstream Docker image or
your Python virtualenv where the main Kiwi TCMS instance is hosted::

    pip install kiwitcms-tenants

then make sure ``KIWI_TENANTS_DOMAIN`` ENV variable is specified !!!
The rest of the settings are installed into ``tcms_settings_dir/multi_tenant.py``
and Kiwi TCMS will pick them up automatically!


First boot configuration
------------------------

When starting your multi-tenant Kiwi TCMS instance for the first time you also
need to create information about the so called public tenant. That is the
default tenant on which your application runs::


    ./manage.py create_tenant --schema_name public
                              --name "Public tenant"
                              --paid_until 2050-12-31
                              --on_trial False
                              --owner_id 2
                              --organization "Testing department"
                              --domain-domain public.tenants.example.org
                              --domain-is_primary True

**WARNING:** schema_name ``public`` is special, the rest is up to you.
``owner_id`` is usually the ID of the first superuser in the database which means
you must have executed ``createsuperuser`` first!

**WARNING:** fresh installations of Kiwi TCMS v8.8 and later contain a special
record with name ``AnonymousUser`` with ID == 1. Super-user will usually have an
ID of 2 in this case! Pay attention to the ``owner_id`` value in the above command!

You can use `create_tenant` afterwards to create other tenants for various teams
or projects. Non-public tenants can also be created via the web interface as well.


DNS configuration
-----------------

You need wildcard DNS resolution to be configured for ``*.tenants.example.org``!

If using AWS Route 53 create an A record with ``Name==*.tenants`` for the
``example.org`` domain and point it to the IP address of your Kiwi TCMS instance.

Once DNS has been configured you should be able to query for various domains with
tools like ``dig`` and ``nslookup``::

    $ dig public.tenant.kiwitcms.org
    ; <<>> DiG 9.11.4-P2-RedHat-9.11.4-12.P2.el7 <<>> public.tenant.kiwitcms.org
    ;; global options: +cmd
    ;; Got answer:
    ;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 58543
    ;; flags: qr rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 1

    ;; OPT PSEUDOSECTION:
    ; EDNS: version: 0, flags:; udp: 4096
    ;; QUESTION SECTION:
    ;public.tenant.kiwitcms.org.    IN      A

    ;; ANSWER SECTION:
    public.tenant.kiwitcms.org. 36  IN      A       100.24.231.234

    ;; Query time: 35 msec
    ;; SERVER: 10.38.5.26#53(10.38.5.26)
    ;; WHEN: Tue Nov 19 14:04:09 EET 2019
    ;; MSG SIZE  rcvd: 71


    $ nslookup linux.tenant.kiwitcms.org
    Server:         10.38.5.26
    Address:        10.38.5.26#53

    Non-authoritative answer:
    Name:   linux.tenant.kiwitcms.org
    Address: 100.24.231.234


All sub-domains should resolve to the same IP address!


Migrating Single-Tenant to Multi-Tenant
---------------------------------------

See `Migrating Single-Tenant to Multi-Tenant
<https://django-tenants.readthedocs.io/en/latest/use.html#migrating-single-tenant-to-multi-tenant>`_
section in the official django-tenants documentation! It has been contributed by the Kiwi TCMS
team and that was the procedure we've used to migrate the previous demo website (ST) to
its new MT version!


Changelog
---------

v1.4.3 (25 Jan 2021)
~~~~~~~~~~~~~~~~~~~~

- Add missing csrf_token in NewTenantForm


v1.4.2 (23 Dec 2020)
~~~~~~~~~~~~~~~~~~~~

- Fix a bug with how we override captcha field in user registration form
- Fix invitation email subject


v1.4 (23 Dec 2020)
~~~~~~~~~~~~~~~~~~

- Tested with Kiwi TCMS v8.9
- Add warning for ``owner_id`` in README
- Replace ModelChoiceField with UserField. Fixes
  `Issue #114 <https://github.com/kiwitcms/tenants/issues/114>`_
- Support user invitions for tenant. Fixes
  `Issue #116 <https://github.com/kiwitcms/tenants/issues/116>`_


v1.3.1 (09 Sep 2020)
~~~~~~~~~~~~~~~~~~~~

- Replace deprecated import to silence warnings with Django 3.1


v1.3 (26 Aug 2020)
~~~~~~~~~~~~~~~~~~

- Tested with Kiwi TCMS v8.6
- Update django-tenants from 3.1.0 to 3.2.1
- Don't pin dependencies in devel.txt


v1.2.1 (24 Jul 2020)
~~~~~~~~~~~~~~~~~~~~

- Filter out AuthorizedUsersChangeForm even on errors
- Tested with Kiwi TCMS v8.5


v1.2 (20 Jun 2020)
~~~~~~~~~~~~~~~~~~

- Update django-tenants from 3.0.3 to 3.1.0
- Improvements in tests and minor updates to make linters happy
- Tested with Kiwi TCMS v8.4


v1.1.1 (27 Apr 2020)
~~~~~~~~~~~~~~~~~~~~

- Do not ship ``TENANT_APPS`` b/c it is distributed with Kiwi TCMS v8.3


v1.1 (25 Apr 2020)
~~~~~~~~~~~~~~~~~~

- Bring back an improved HTML placeholder for schema_name
- Properly validate input values for schema/domain names


v1.0.3 (24 Apr 2020)
~~~~~~~~~~~~~~~~~~~~

- Always lower case schema_name to make sure it can actually be
  used as a valid hostname


v1.0.2 (24 Apr 2020)
~~~~~~~~~~~~~~~~~~~~

- Update django-tenants from 3.0.1 to 3.0.3
- Show valid schema_name pattern as help text in UI
- Remove schema_name placeholder text because it was misleading


v1.0.1 (18 Mar 2020)
~~~~~~~~~~~~~~~~~~~~

- Slightly adjust default values for settings ``TENANT_APPS`` and
  ``MULTITENANT_RELATIVE_MEDIA_ROOT`` to match Kiwi TCMS and installations
  prior to turning this package into a plugin. This will avoid dusrupting
  existing deployments!


v1.0 (15 Mar 2020)
~~~~~~~~~~~~~~~~~~

- Turn into proper Kiwi TCMS plugin and install settings overrides under
  ``tcms_settings_dir/`` (compatible with Kiwi TCMS v8.2 or later)
  
  - does not need ``MENU_ITEMS`` and ``ROOT_URLCONF`` override anymore
  - does not need to load ``tcms_tenants`` in ``INSTALLED_APPS`` manually
  - only need to specify ``KIWI_TENANTS_DOMAIN`` env variable!
- Require ``tcms_tenants.add_tenant`` permission for ``NewTenantView``
- Reimplement ``NewTenantView`` as ``FormView``
- Refactor ``redirect_to()`` to class based view
- Add tests for admin.py. Closes #5
  `Issue #5 <https://github.com/kiwitcms/tenants/issues/5>`_
- Replace ``datetime.now`` with ``timezone.now`` for better support of
  installations with enabled timezone config
- Enable pylint. Closes
  `Issue #17 <https://github.com/kiwitcms/tenants/issues/17>`_
- Enable flake8


v0.5.1 (17 Feb 2020)
~~~~~~~~~~~~~~~~~~~~

- Update django-tenants from 3.0.0 to 3.0.1. Fixes
  `Issue #60 <https://github.com/kiwitcms/tenants/issues/60>`_


v0.5 (16 Jan 2020)
~~~~~~~~~~~~~~~~~~

- Bump django-tenants from 2.2.3 to 3.0.0
- Tested successfully against Kiwi TCMS v7.3 with Django 3.0


v0.4.7 (11 Dec 2019)
~~~~~~~~~~~~~~~~~~~~

- Set ``tcms_tenants.tests.LoggedInTestCase.tenant.owner.password`` to
  "password" so it can be reused by downstream tests


v0.4.6 (11 Dec 2019)
~~~~~~~~~~~~~~~~~~~~

- New translations for Slovenian
- Replace ugettext_lazy with gettext_lazy for Django 3.0
- Start shipping ``tcms_tenants.tests`` to be used by other multi-tenant
  add-on packages
- Confirmed working against Kiwi TCMS v7.2


v0.4.5 (24 Nov 2019)
~~~~~~~~~~~~~~~~~~~~

- Document how to configure multi-tenancy
- Document ST to MT migration
- Add helper method ``create_oss_tenant()``
- Internal updates to ``TENANT_APPS`` while testing


v0.4.4 (29 Oct 2019)
~~~~~~~~~~~~~~~~~~~~

- New translations for Russian


v0.4.3 (18 May 2019)
~~~~~~~~~~~~~~~~~~~~

- Add ``Tenant.organization`` field
- When creating tenant set site.name to tenant.domain.domain


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
