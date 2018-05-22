import traceback

from flask import current_app
from flaskext.xmlrpc import XMLRPCHandler, Fault

from product_listings_manager import products

handler = XMLRPCHandler('xmlrpc')


@handler.register
def getProductInfo(*a, **kw):
    try:
        return products.getProductInfo(*a, **kw)
    except Exception as e:
        err = traceback.print_exc()
        current_app.logger.error(err)
        raise Fault(e)


@handler.register
def getProductListings(*a, **kw):
    try:
        return products.getProductListings(*a, **kw)
    except Exception as e:
        err = traceback.print_exc()
        # import pdb; pdb.set_trace()
        current_app.logger.error(err)
        raise Fault(e)
