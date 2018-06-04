from flask import Flask, request, jsonify

from product_listings_manager import rest_api_v1, xmlrpc
from product_listings_manager import products

app = Flask(__name__)

# Set products.py's DB values from our Flask config:
app.config.from_object('product_listings_manager.config')
app.config.from_pyfile('/etc/product-listings-manager/config.py', silent=True)
app.config.from_envvar('FLASK_CONFIG', silent=True)
products.dbname = app.config['DBNAME'] # eg. "compose"
products.dbhost = app.config['DBHOST'] # eg "db.example.com"
products.dbuser = app.config['DBUSER'] # eg. "myuser"
products.dbpasswd = app.config['DBPASSWD'] # eg. "mypassword"

app.register_blueprint(rest_api_v1.blueprint, url_prefix='/api/v1.0')
xmlrpc.handler.connect(app, '/xmlrpc')


@app.errorhandler(404)
def page_not_found_error(ex):
    if not request.path.startswith('/xmlrpc'):
        return jsonify({'error': str(ex)})


if __name__ == '__main__':
    app.run()
