from flask import Flask

from product_listings_manager import rest_api_v1, xmlrpc

app = Flask(__name__)
app.register_blueprint(rest_api_v1.blueprint, url_prefix='/api/v1.0')
xmlrpc.handler.connect(app, '/xmlrpc')

if __name__ == '__main__':
    app.run()
