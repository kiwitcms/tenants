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

    ./manage.py initial_setup

Your tenant will be available at https://$KIWI_TENANTS_DOMAIN!
Other tenants can be created via the web interface and will be available
under team-01.$KIWI_TENANTS_DOMAIN, product-02.$KIWI_TENANTS_DOMAIN, etc
depnding on the actual ``schema name`` you give them.


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


Local Development
-----------------

Starting with Kiwi TCMS v13.1 session and CSRF cookies are configured only on HTTPS
connections which will prevent browsers from sending cookies over a plain text HTTP
connection. This will result in not being able to login if you are using a local
development server. To workaround this issue, first generate an SSL certificate::

    /usr/bin/sscg -v -f --country BG --locality Sofia --organization "Kiwi TCMS" --organizational-unit "QA" --ca-file ssl/ca.crt --cert-file ssl/host.crt --cert-key-file ssl/host.key

Then use the ``runerver_plus`` command to start Kiwi TCMS development server with HTTPS::

    PYTHONPATH=../Kiwi/ KIWI_TENANTS_DOMAIN=tenant.example.bg ./manage.py runserver_plus --cert-file ssl/host.crt  --key-file ssl/host.key

Then point your browser to https://tenant.example.bg:8000/.
The SSL warning from the browser is expected!

You can use your `OS hosts file <https://en.wikipedia.org/wiki/Hosts_(file)>`_
to configure DNS resolution during development::

    127.0.0.1   localhost tenant.example.bg empty.tenant.example.bg


Changelog
---------

v2.7.0 (24 Apr 2024)
~~~~~~~~~~~~~~~~~~~~

- Add the ``Tenant.extra_emails`` field for storing information like
  technical email, billing email, etc. To be used by add-on tools
- Add the ``initialize_tenants`` management command
- Update local development instructions
- Enable code formatting with ``black``
- Start testing using upstream Postgres container
- Execute CodeQL on pull request and branches
- Adjust tests for Django 5.0


v2.6.1 (08 Mar 2024)
~~~~~~~~~~~~~~~~~~~~

- Remove use of ``non-existing.png`` file in tenant name area
  to avoid 404 responses which trigger rate limiting


v2.6.0 (14 Jan 2024)
~~~~~~~~~~~~~~~~~~~~

- Update django-tenants from 3.5.0 to 3.6.1
- Update pylint-django from 2.5.3 to 2.5.5
- Start building and testing with Python 3.11
- Start testing with psycopg3


v2.5.2 (24 Oct 2023)
~~~~~~~~~~~~~~~~~~~~

- Add ``trackers_integration`` into ``tenant_groups.models.Group.relevant_apps``
  to allow per-tenant assignment for permissions around personal API
  tokens, see https://github.com/kiwitcms/trackers-integration/pull/44


v2.5.1 (12 May 2023)
~~~~~~~~~~~~~~~~~~~~

- Update to django-tenants==3.5.0
- Replace ``form_errors_to_list()`` which was removed in Kiwi TCMS v12.2


v2.5.0 (10 Feb 2023)
~~~~~~~~~~~~~~~~~~~~

- Update to django-tenants==3.4.8
- Bug fix on Create Tenant page for Kiwi TCMS v11.7 or later


v2.4.0 (15 Nov 2022)
~~~~~~~~~~~~~~~~~~~~

- Allow customization of tenant logo in navigation (Ivajlo Karabojkov)
- Add CodeQL workflow for GitHub code scanning
- Fix make messages command


v2.3.2 (31 Oct 2022)
~~~~~~~~~~~~~~~~~~~~

- Update django-tenants from 3.4.5 to 3.4.7
- Don't add users to TenantGroup on ``empty`` tenant
- Adjust redirects from Tenant admin page to avoid confusion
- Update docs for initial configuration
- Add more assertions into test


v2.3.1 (10 Sep 2022)
~~~~~~~~~~~~~~~~~~~~

- Don't access ``request.tenant`` if such attribute does not exist. Fixes
  `KIWI-TCMS-K2 <https://sentry.io/organizations/kiwitcms/issues/3565864401/>`_


v2.3.0 (02 Sep 2022)
~~~~~~~~~~~~~~~~~~~~

- Don't grant ``auth.view_`` permissions even on publicly readable tenants
- Honor ``settings.DEFAULT_GROUPS`` instead of hard-coding. Invited users and
  users authorized via the Admin panel will be added to tenant groups which
  match ``settings.DEFAULT_GROUPS`` ("Tester" by default) if such tenant groups
  exist. If the setting is an empty list or there are no tenant groups matching
  the specific names configured then authorized users will be left without
  group associations. It will be up to a Kiwi TCMS administrator to
  manually assign permissions and tenant groups for each user.


v2.2.1 (30 Aug 2022)
~~~~~~~~~~~~~~~~~~~~

- Fix a bug in the ``create_oss_tenant()`` helper function


v2.2.0 (14 Aug 2022)
~~~~~~~~~~~~~~~~~~~~

- Update django-tenants from 3.4.2 to 3.4.4
- Show tenant information in navigation (Ivajlo Karabojkov)
- Allow editing Tenant.name to make it easier for admins to customize the
  text shown in navigation!
- Internal updates around testing and CI


v2.1.1 (27 Apr 2022)
~~~~~~~~~~~~~~~~~~~~

- Don't crash if user can't change tenant groups. Fixes
  `KIWI-TCMS-J8 <https://sentry.io/organizations/kiwitcms/issues/3230191406/>`_


v2.1.0 (27 Apr 2022)
~~~~~~~~~~~~~~~~~~~~

- Add ``refresh_tenant_permissions`` command which will be executed automatically
  by ``refresh_permissions``


v2.0.1 (19 Apr 2022)
~~~~~~~~~~~~~~~~~~~~

- Fix URL is help message


v2.0.0 (18 Apr 2022)
~~~~~~~~~~~~~~~~~~~~

- Define per-tenant ``Group`` model and add an authentication backend which will
  consume permissions from tenant-groups. Closes #104
  `Issue #104 <https://github.com/kiwitcms/tenants/issues/104>`_
- Add pre-commit CI config & apply automatic fixes


v1.11.0 (24 Jan 2022)
~~~~~~~~~~~~~~~~~~~~~

- Add System check for ``KIWI_TENANTS_DOMAIN`` environment variable. Closes
  `Issue #140 <https://github.com/kiwitcms/tenants/issues/140>`_


v1.10.0 (19 Jan 2022)
~~~~~~~~~~~~~~~~~~~~~

- Update django-tenants from 3.4.1 to 3.4.2,
  will help with migration to Django 4


v1.9.0 (10 Jan 2022)
~~~~~~~~~~~~~~~~~~~~

- Update django-tenants from 3.3.4 to 3.4.1
- Update expected error message for tests
- Fix code coverage uploads


v1.8.0 (16 Oct 2021)
~~~~~~~~~~~~~~~~~~~~

- Update django-tenants from 3.3.2 to 3.3.4. Fixes a bug for cloning tenants
  when DB username contains a dash
- Use f-strings b/c pylint really loves them


v1.7.0 (03 Sep 2021)
~~~~~~~~~~~~~~~~~~~~

- Faster tenant creation with ``clone_tenant``. Fixes
  `Issue #127 <https://github.com/kiwitcms/tenants/issues/127>`_
  Requires a schema with name ``empty`` to be present!
- Fix pylint warnings
- Migrate from Travis CI to GitHub Actions


v1.6.0 (18 Jun 2021)
~~~~~~~~~~~~~~~~~~~~

- Update django-tenants from 3.3.1 to 3.3.2
- More robust tenant domain detection to avoid bugs in the case where
  public tenant's domain doesn't use a prefix (e.g. matches KIWI_TENANT_DOMAIN)


v1.5.0 (04 Jun 2021)
~~~~~~~~~~~~~~~~~~~~

- Database: Rename ``Tenant.on_trial`` -> ``Tenant.publicly_readable``
- Allow unauthorized users to access publicly readable tenants
- Update django-tenants from 3.3.0 to 3.3.1
- Update translation strings
- Tested with Kiwi TCMS v10.1
- Convert ``NewTenantForm`` to inherit from ``ModelForm``


v1.4.4 (12 May 2021)
~~~~~~~~~~~~~~~~~~~~

- Update django-tenants from 3.2.1 to 3.3.0
- Tested with Kiwi TCMS v10.0
- Tested with Python 3.8


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
