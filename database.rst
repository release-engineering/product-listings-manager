set up a composedb instance for testing
=======================================

This walkthrough explains how to set up a dedicated Postgres VM for Product
Listings Manager's database.


Host OS
-------

Currently the production compose database environment is RHEL 5 with
postgresql-8.2.14-1.el5s2 .

There are plans to upgrade this server to RHEL 7, so you may as well use RHEL 7
in your VM.

Installing the postgresql server package
----------------------------------------

Install the ``postgresql-server`` package::

    yum install postgresql-server

Initialize the database storage location.

On RHEL 5::

    su - postgres -c "initdb /var/lib/pgsql/data"

On RHEL 7::

    postgresql-setup initdb

Allow network connections
-------------------------

Edit ``/var/lib/pgsql/data/pg_hba.conf`` and add the line::

    host    all             all             0.0.0.0/0           trust

On RHEL 7, you'll also need IPv6, because libpq connections to "localhost" use
IPv6 by default::

    host    all             all             ::1/0               trust

(... note, "trust" gives full admin rights to all users from anywhere.)

Edit ``/var/lib/pgsql/data/postgresql.conf`` and add the line::

    listen_addresses = '*'

Start and Enable the service
----------------------------

This is straightforward.

On RHEL 5::

    service postgresql start
    chkconfig postgresql on

On RHEL 7::

    systemctl start postgresql
    systemctl enable postgresql

Sanity-check that the daemon is listening on all interfaces::

    netstat -an | grep 5432

This should should show postgres listening on ``0.0.0.0:5432``.

Connecting
----------

On your local workstation, connect to your Posgres VM's IP address. Here's an
example connecting to Postgres on RHEL 7::

  psql -h 192.168.122.124 -U postgres

  postgres=# select VERSION();
   PostgreSQL 9.2.23 on x86_64-redhat-linux-gnu, compiled by gcc (GCC) 4.8.5 20150623 (Red Hat 4.8.5-16), 64-bit
   (1 row)

Compare this to production composedb environment (currently RHEL 5)::

  psql -h (hostname) -U (username) compose -W -c "select VERSION();"
   PostgreSQL 8.2.14 on x86_64-redhat-linux-gnu, compiled by GCC gcc (GCC) 4.1.2 20080704 (Red Hat 4.1.2-46)


The ``\q`` command will quit the ``psql`` prompt.

Create the application user
---------------------------

On your local workstation, you can use the ``createuser`` shell utility
(``postgresql`` package) to create the "compose_ro" user account::

  createuser -h 192.168.122.124 -U postgres -P --no-createdb --no-createrole compose_ro

``createuser`` will prompt you to set a password for this new user.

Create the application database
-------------------------------

On your local workstation, you can use the ``createdb`` shell utility
(``postgresql`` package) to create the "compose" database::

  createdb -h 192.168.122.124 -U postgres --encoding SQL_ASCII compose

On RHEL 7, you must append ``--template template0`` to this command.

Note, the encoding is important, because this is what is set on the prod
server. *If* you forgot to set ``--encoding`` during ``createdb`` above, you
can set it later::

  update pg_database set encoding = pg_char_to_encoding('SQL_ASCII') where datname = 'compose';

If you don't set the encoding here, you cannot import data dumps from
the production server.

Dumping and restoring tables from production
--------------------------------------------

products.py needs the following tables::

  match_versions
  overrides
  packages
  products
  tree_packages
  tree_product_map
  trees

You can use ``db_dump`` to obtain these from production. Here are the file
sizes from ``db_dump``'s custom compressed format::

    697  match_versions
    666K overrides.backup
    157M packages.backup
    31K  products.backup
    1.3G tree_packages.backup
    7.1M trees.backup

Note: the ``tree_packages`` table is 1.3GB compressed (unknown size
uncompressed). It took 18 minutes to dump from prod over my VPN connection
(1.25MB/s).

I've not yet been able to restore this ``tree_packages`` table to a development
VM. On RHEL 5, ``pg_restore`` churns for an hour and then OOMs even with 4GB
RAM. On RHEL 7 ``pg_restore`` does not leak memory, but I kept running out of
disk space in ``/var/lib/pgsql/data``. It took up 50GB of space before I gave
up.

Diffing schemas from production
-------------------------------

The production database schema has been managed by hand over the years, so we
need to reverse-engineer it into something that we can reproduce with
SQLAlchemy. To do that, it's helpful to compare the development server's schema
with the production server.

Connect your ``psql`` client to both databases.

Use ``\dt`` to list all tables, and ``\d+ tablename`` to show the schemas for
each table.

::

    compose=> \d+ match_versions
                              Table "public.match_versions"
     Column  |          Type          | Modifiers | Storage  | Stats target | Description
    ---------+------------------------+-----------+----------+--------------+-------------
     name    | character varying      |           | extended |              |
     product | character varying(100) |           | extended |              |
    Indexes:
        "match_versions_un" UNIQUE, btree (name, product)
    Has OIDs: yes


You can compare the output of ``\d+`` in both environments.
