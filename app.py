import traceback
from flask import Flask
from flask_xmlrpcre.xmlrepcre import XMLRPCHandler, Fault

import products

app = Flask(__name__)

handler = XMLRPCHandler('xmlrpc')
handler.connect(app, '/xmlrpc')


@handler.register
def getProductInfo(*a, **kw):
    try:
        return products.getProductInfo(*a, **kw)
    except Exception as e:
        err = traceback.print_exc()
        app.logger.error(err)
        raise Fault(e)


@handler.register
def getProductListings(*a, **kw):
    try:
        return products.getProductListings(*a, **kw)
    except Exception as e:
        err = traceback.print_exc()
        # import pdb; pdb.set_trace()
        app.logger.error(err)
        raise Fault(e)


if __name__ == '__main__':
    app.run()
