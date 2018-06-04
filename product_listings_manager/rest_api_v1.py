from flask import Blueprint, url_for
from flask_restful import Resource, Api

from product_listings_manager import __version__, products

blueprint = Blueprint('api_v1', __name__)


class Index(Resource):
    def get(self):
        """ Link to the the v1 API endpoints. """
        return {
            'about_url': url_for('.about', _external=True),
            'product_info_url': url_for('.productinfo',
                                        label=':label',
                                        _external=True),
            'product_listings_url': url_for('.productlistings',
                                            label=':label',
                                            build_info=':build_info',
                                            _external=True),
        }


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
api.add_resource(Index, '/')
api.add_resource(About, '/about')
api.add_resource(ProductInfo, '/product-info/<label>')
api.add_resource(ProductListings, '/product-listings/<label>/<build_info>')
