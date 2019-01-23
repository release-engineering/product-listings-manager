from flask import Blueprint, url_for
from flask_restful import Resource, Api

from product_listings_manager import __version__, products, utils

from werkzeug.exceptions import NotFound

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
            'module_product_listings_url': url_for('.moduleproductlistings',
                                                   label=':label',
                                                   module_build_nvr=':module_build_nvr',
                                                   _external=True),
        }


class About(Resource):
    def get(self):
        return {'version': __version__}


class ProductInfo(Resource):
    def get(self, label):
        try:
            versions, variants = products.getProductInfo(label)
        except products.ProductListingsNotFoundError as ex:
            raise NotFound(str(ex))
        except Exception:
            utils.log_remote_call_error('API call getProductInfo() failed', label)
            raise
        return [versions, variants]


class ProductListings(Resource):
    def get(self, label, build_info):
        try:
            return products.getProductListings(label, build_info)
        except products.ProductListingsNotFoundError as ex:
            raise NotFound(str(ex))
        except Exception:
            utils.log_remote_call_error('API call getProductListings() failed', label, build_info)
            raise


class ModuleProductListings(Resource):
    def get(self, label, module_build_nvr):
        try:
            return products.getModuleProductListings(label, module_build_nvr)
        except products.ProductListingsNotFoundError as ex:
            raise NotFound(str(ex))
        except Exception:
            utils.log_remote_call_error('API call getModuleProductListings() failed', label, module_build_nvr)
            raise


api = Api(blueprint)
api.add_resource(Index, '/')
api.add_resource(About, '/about')
api.add_resource(ProductInfo, '/product-info/<label>')
api.add_resource(ProductListings, '/product-listings/<label>/<build_info>')
api.add_resource(ModuleProductListings, '/module-product-listings/<label>/<module_build_nvr>')
