product-listings-manager
========================

.. image:: https://travis-ci.org/release-engineering/product-listings-manager.svg?branch=master
          :target: https://travis-ci.org/release-engineering/product-listings-manager

.. image:: https://copr.fedorainfracloud.org/coprs/ktdreyer/product-listings-manager/package/product-listings-manager/status_image/last_build.png
          :target: https://copr.fedorainfracloud.org/coprs/ktdreyer/product-listings-manager/package/product-listings-manager/

.. image:: https://quay.io/repository/redhat/product-listings-manager/status
          :target: https://quay.io/repository/redhat/product-listings-manager

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

Installation and setup
----------------------

1. Install the prerequisite system packages::

   $ sudo dnf -y install postgresql-devel krb5-devel rpm-devel gcc python-devel python3-virtualenvwrapper

2. Set up a virtualenv::

   $ mkvirtualenv -p python3 plm

  ... Run ``source /usr/bin/virtualenvwrapper.sh`` if ``mkvirtualenv`` command not available

3. Install the prerequisite packages::

   $ workon plm
   $ pip install -r requirements.txt

4. Create ``config.py`` with the database settings::

   $ echo "SQLALCHEMY_DATABASE_URI = 'postgresql://myusername:mypass@dbhost/dbname'" > config.py
   $ vi config.py

5. Set the ``PLM_CONFIG_FILE`` environment variable to the full filesystem path of
   this new file::

   $ export PLM_CONFIG_FILE=$(pwd)/config.py

6. Install brewkoji package. This creates ``/etc/koji.conf.d/brewkoji.conf``,
   so ``products.py`` can contact the Brew hub::

   $ sudo dnf -y install brewkoji

7. Trust Brew's SSL certificate::

   $ export REQUESTS_CA_BUNDLE=/etc/pki/ca-trust/source/anchors/RH-IT-Root-CA.crt

  ... Or if you've installed this globally on your system, tell requests to use
  your global CA store::

   $ export REQUESTS_CA_BUNDLE=/etc/pki/tls/certs/ca-bundle.crt

8. Run the server::

   $ FLASK_APP=product_listings_manager.app flask run

The Flask web server will run on TCP 5000.

You can access the http://localhost:5000/ at that point.

Running the tests
-----------------

Install required packages for test::

   $ pip install -r test-requirements.txt

You can invoke the tests with ``tox``::

   $ tox

Alternatively, you can run pytest directly::

   $ pytest --cov=product_listings_manager tests

Using the ``--live`` argument if you want to run against the live composedb instance::

   $ pytest --cov=product_listings_manager --live tests


Configuring a local database
----------------------------

See ``database.rst`` for instructions to configure a local postgres instance.
