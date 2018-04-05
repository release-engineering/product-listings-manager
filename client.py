from __future__ import print_function
from pprint import pprint
import argparse
import xmlrpclib

SERVERS = {
    'brew': 'https://brewhub.engineering.redhat.com/brewhub',
    'localhost': 'http://localhost:5000/xmlrpc',
}

parser = argparse.ArgumentParser()
parser.add_argument('server', choices=SERVERS.keys())
args = parser.parse_args()

url = SERVERS[args.server]
server = xmlrpclib.ServerProxy(url)

# Test getProductInfo
result = server.getProductInfo("RHEL-6-Server-EXTRAS-6")
pprint(result)

# Test getProductListings
# Example with brew CLI:
#  brew call getProductListings "RHEL-6-Server-EXTRAS-6" "dumb-init-1.2.0-1.20170802gitd283f8a.el6"
result = server.getProductListings("RHEL-6-Server-EXTRAS-6", "dumb-init-1.2.0-1.20170802gitd283f8a.el6")
pprint(result)
