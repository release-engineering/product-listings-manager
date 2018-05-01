product-listings-manager
========================

HTTP interface for finding product listings and interacting with data in
composedb.

Previously this mechanism was a Koji plugin. This ``product-listings-manager``
project extracts the plugin into its own web service apart from Koji.

XML-RPC
-------

You may call the ``getProductListings`` API call on ``<url>/xmlrpc``. This
works the same way that the Brew call does. See ``client.py`` for an example.

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

Installation and setup
----------------------

1. Set up a virtualenv::

   $ virtualenv venv

2. Activate the virtualenv::

   $ . venv/bin/activate

3. Install the prerequisite packages::

   $ python setup.py install

4. Create ``instance/config.py`` with the database settings::

   $ cp config.py instance/config.py
   $ vi instance/config.py

5. Install brewkoji package. This creates ``/etc/koji.conf.d/brewkoji.conf``,
   so ``products.py`` can contact the Brew hub::

   $ sudo yum -y install brewkoji

6. Trust Brew's SSL certificate::

   $ export REQUESTS_CA_BUNDLE=/etc/pki/ca-trust/source/anchors/RH-IT-Root-CA.crt

7. Run the server::

   $ FLASK_APP=product_listings_manager flask run

The Flask web server will run on TCP 5000.

You can access the http://localhost:5000/xmlrpc at that point.

Running the tests
-----------------

Install pytest, then run it for the ``tests/`` directory::

   $ pip install pytest
   $ python -m pytest tests/
