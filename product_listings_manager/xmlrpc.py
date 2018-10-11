from flaskext.xmlrpc import XMLRPCHandler, Fault

from product_listings_manager import products, utils

handler = XMLRPCHandler('xmlrpc')


@handler.register
def getProductInfo(*a, **kw):
    try:
        return products.getProductInfo(*a, **kw)
    except Exception:
        utils.log_remote_call_error('XMLRPC call getProductInfo() failed', *a, **kw)
        raise Fault(1, 'An unexpected error has occurred.')


@handler.register
def getProductListings(*a, **kw):
    try:
        return products.getProductListings(*a, **kw)
    except Exception:
        utils.log_remote_call_error('XMLRPC call getProductListings() failed', *a, **kw)
        raise Fault(1, 'An unexpected error has occurred.')
