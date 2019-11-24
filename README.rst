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


Installation
------------

**IMPORTANT:** multi-tenancy is backed by PostgreSQL schemas! It will not work
with a different database backend.

**WARNING:** current tenant is decided based on the FQDN by which you
are accessing Kiwi TCMS!

The following changes need to be introduced into a downstream Docker image or
your Python virtualenv where the main Kiwi TCMS instance is hosted::

    pip install kiwitcms-tenants

Then make sure the following settings are configured::

    DATABASES['default']['ENGINE'] = 'django_tenants.postgresql_backend'
    DATABASE_ROUTERS = ['django_tenants.routers.TenantSyncRouter']

    # TenantMainMiddleware must be the first in the list
    MIDDLEWARE.insert(0, 'django_tenants.middleware.main.TenantMainMiddleware')
    MIDDLEWARE.append('tcms_tenants.middleware.BlockUnauthorizedUserMiddleware')

    TENANT_MODEL = "tcms_tenants.Tenant"
    TENANT_DOMAIN_MODEL = "tcms_tenants.Domain"

    # django_tenants & tcms_tenants must be the first in the list
    INSTALLED_APPS.insert(0, 'django_tenants')
    INSTALLED_APPS.insert(1, 'tcms_tenants')

    # list INSTALLED_APPS which will have their own copy for different tenants
    TENANT_APPS = [ ... ]

    SHARED_APPS = INSTALLED_APPS

    # public tenant will be at https://public.tenants.example.org
    # Wild card DNS must be configured
    KIWI_TENANTS_DOMAIN = 'tenants.example.org'

    SESSION_COOKIE_DOMAIN = ".%s" % KIWI_TENANTS_DOMAIN

    # attachments storage
    DEFAULT_FILE_STORAGE = "tcms_tenants.storage.TenantFileSystemStorage"
    MULTITENANT_RELATIVE_MEDIA_ROOT = "tenants/%s"

    # override the default ROOT_URLCONF!
    ROOT_URLCONF = 'test_project.urls'

    # (optional) create new item in navigation menu
    MENU_ITEMS.append(
        (_('TENANT'), [
            (_('Create'), reverse_lazy('tcms_tenants:create-tenant')),
            ('-', '-'),
            (_('Authorized users'), '/admin/tcms_tenants/tenant_authorized_users/'),
        ]),
    )

Check
`test_project/settings.py <https://github.com/kiwitcms/tenants/blob/master/test_project/settings.py>`_
and `test_project/urls.py <https://github.com/kiwitcms/tenants/blob/master/test_project/urls.py>`_
for more examples.


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


v0.4.5 (24 Nov 2019)
~~~~~~~~~~~~~~~~~~~~

- Document how to configure multi-tenancy
- Document ST to MT migration
- Add helper method ``create_oss_tenant()``
- INternal updates to ``TENANT_APPS`` while testing


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
