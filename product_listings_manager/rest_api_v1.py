from flask import Blueprint
from flask_restful import Resource, Api

from product_listings_manager import __version__, products

blueprint = Blueprint('api_v1', __name__)


class About(Resource):
    def get(self):
        return {'version': __version__}


class ProductInfo(Resource):
    def get(self, label):
        versions, variants = products.getProductInfo(label)
        return [versions, variants]


class ProductListings(Resource):
    def get(self, label, build_info):
        return products.getProductListings(label, build_info)


api = Api(blueprint)
api.add_resource(About, '/about')
api.add_resource(ProductInfo, '/product-info/<label>')
api.add_resource(ProductListings, '/product-listings/<label>/<build_info>')
