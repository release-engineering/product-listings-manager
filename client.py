#!/usr/bin/env python

import argparse
import json

SERVERS = {
    "brew": "https://brewhub.engineering.redhat.com/brewhub",
    "local": "http://localhost:5000/api/v1.0",
    "dev1": "http://prodlistings-dev1.usersys.redhat.com/api/v1.0",
}

parser = argparse.ArgumentParser()
parser.add_argument("server", choices=SERVERS.keys())
parser.add_argument("--product", default="RHEL-6-Server-EXTRAS-6")
parser.add_argument(
    "--nvr", default="dumb-init-1.2.0-1.20170802gitd283f8a.el6"
)
args = parser.parse_args()

url = SERVERS[args.server]


def pretty_print_json(data):
    print(json.dumps(data, indent=4))


if args.server == "brew":
    import xmlrpclib  # nosec

    server = xmlrpclib.ServerProxy(url)

    # Test getProductInfo
    result = server.getProductInfo(args.product)
    pretty_print_json(result)

    # Test getProductListings
    # Example with brew CLI:
    #  brew call getProductListings "RHEL-6-Server-EXTRAS-6" \
    #    "dumb-init-1.2.0-1.20170802gitd283f8a.el6"
    result = server.getProductListings(args.product, args.nvr)
    pretty_print_json(result)
else:
    import requests

    product_info_path = "/product-info/%s" % args.product
    product_listings_path = "/product-listings/{}/{}".format(
        args.product,
        args.nvr,
    )

    for path in (product_info_path, product_listings_path):
        result = requests.get(url + path, timeout=30)
        result.raise_for_status()
        data = result.json()
        pretty_print_json(data)
