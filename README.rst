product-listings-manager
========================

.. image:: https://quay.io/repository/redhat-user-workloads/exd-sp-rhel-wf-tenant/plm/status
          :target: https://quay.io/repository/redhat-user-workloads/exd-sp-rhel-wf-tenant/plm

.. image:: https://coveralls.io/repos/github/release-engineering/product-listings-manager/badge.svg?branch=master
          :target: https://coveralls.io/github/release-engineering/product-listings-manager?branch=master


HTTP interface for finding product listings and interacting with data in
composedb.

Previously this mechanism was a Koji plugin. This ``product-listings-manager``
project extracts the plugin into its own web service apart from Koji.

REST API
--------

You may use HTTP GET request to get ``/api/v1.0/product-info/<PRODUCT>`` or
``/api/v1.0/product-listings/<PRODUCT>/<BUILD_INFO>``. The parameters and
results are same as for the XML-RPC ``getProductInfo`` and
``getProductListings`` calls used in Brew. See ``client.py`` for an example.

What is ComposeDB?
------------------

All RPM-based products shipped through the Errata Tool use ComposeDB for
"product listings".

ComposeDB defines a product by mapping RPMs to products/variants/arches.

Goals with this project
-----------------------

* Implement the Brew plugin's API and functionality exactly, in order to
  minimize Errata Tool changes when migrating to this new service.

* Eliminate Brew/Koji's constraint of using XML-RPC

* Decouple the development of this service so that it is easier to develop,
  test, and deploy apart from Brew's prod environment.

Architecture diagram
--------------------

.. image:: misc/prod-listings-manager.png
    :width: 958px
    :align: center
    :height: 364px
    :alt: product-listings-manager architecture diagram

Running the tests
-----------------

You can invoke the tests with ``tox``::

   $ tox

Using the ``--live`` argument if you want to run against the live composedb instance::

   $ tox -e py3 -- --cov=product_listings_manager --live tests

Running the linters
-------------------

To run viable linters to check syntax of various files before commit, install
`pre-commit <https://pre-commit.ci/>`__ and run::

    $ pre-commit install

To run linters on all files (not just the ones changed in the last commit),
run::

    $ pre-commit run -a

Setting up local environment
----------------------------

You can use ``docker-compose`` or ``podman-compose`` to start:

- product-listings-manager - the web service running at ``http://localhost:8080``
- postgres - database for product-listings-manager, initialized with all
  ``*.sql`` files in ``docker/docker-entrypoint-initdb.d`` directory
- jaeger - collector and query service for OpenTelemetry traces collected from
  the local instance of product-listings-manager and the database, running at
  ``http://localhost:16686``

Rebuild product-listings-manager image::

    $ podman-compose build

Image rebuild is needed only if dependencies change. The container running in
the compose environment uses the current source code directory.

Start the services::

    $ podman-compose up

Show logs::

    $ podman-compose logs plm
    $ podman-compose logs plm-db
    $ podman-compose logs jaeger

Restart product-listings-manager::

    $ podman-compose restart plm

Stop the services::

    $ podman-compose up

Configuration
-------------

The service is conteinerized application and uses environment variables for
configuration:

- ``SQLALCHEMY_DATABASE_URI`` - full database URI for SQLAlchemy, for example:
  ``postgresql://username:password@plm-db.example.com:5433/plm``
- ``OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`` - traces endpoint for OpenTelemetry
  tracing, for example: ``https://otel.example.com/v1/traces``
- ``OTEL_EXPORTER_SERVICE_NAME`` - service name for OpenTelemetry tracing
- ``PLM_KOJI_CONFIG_PROFILE`` - Koji profile to use (in ``/etc/koji.conf.d/``
  directory), default is ``brew``
- ``PLM_LDAP_HOST`` - LDAP host, for example ``ldaps://ldap.example.com``
- ``PLM_LDAP_SEARCHES`` - JSON formatted array with LDAP search base and search
  template, for example:

  .. code-block:: json

      [{"BASE": "ou=Groups,dc=example,dc=com", "SEARCH_STRING": "(memberUid={user})"}]

- ``PLM_PERMISSIONS`` - JSON formatted array with permissions, for example:

  .. code-block:: json

      [
        {
          "name": "admins",
          "description": "product-listings-manager admins",
          "contact": "plm-admins@example.com",
          "queries": ["*"],
          "groups": ["plm-admins"],
          "users": ["alice", "bob"]
        },
        {
          "name": "viewers",
          "queries": ["SELECT *"],
          "groups": ["plm-users"]
        }
      ]

- ``PLM_RESPONSE_HEADERS`` - JSON formatted object with additional headers to
  add to responses; the default is:

  .. code-block:: json

      {"Strict-Transport-Security": "max-age=31536000; includeSubDomains"}
