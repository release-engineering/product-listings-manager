from flask import Flask, jsonify

from product_listings_manager import rest_api_v1, root
from product_listings_manager.config import load_config
from product_listings_manager.logger import init_logging
from product_listings_manager.models import db


def page_not_found_error(ex):
    return jsonify({"error": str(ex)}), 404


def create_app():
    app = Flask(__name__)

    load_config(app)
    init_logging(app)
    db.init_app(app)

    app.register_error_handler(404, page_not_found_error)
    app.register_blueprint(root.blueprint, url_prefix="/")
    app.register_blueprint(rest_api_v1.blueprint, url_prefix="/api/v1.0")
    return app
