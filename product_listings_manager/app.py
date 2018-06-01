from flask import Flask

from product_listings_manager import rest_api_v1, xmlrpc
from product_listings_manager import products

app = Flask(__name__)

# Set products.py's DB values from our Flask config:
app.config.from_object('product_listings_manager.config')
app.config.from_envvar('FLASK_CONFIG')
products.dbname = app.config['DBNAME'] # eg. "compose"
products.dbhost = app.config['DBHOST'] # eg "db.example.com"
products.dbuser = app.config['DBUSER'] # eg. "myuser"
products.dbpasswd = app.config['DBPASSWD'] # eg. "mypassword"

app.register_blueprint(rest_api_v1.blueprint, url_prefix='/api/v1.0')
xmlrpc.handler.connect(app, '/xmlrpc')

if __name__ == '__main__':
    app.run()
