from flask import Blueprint, url_for
from flask_restful import Resource, Api

blueprint = Blueprint('/', __name__)


DOCUMENTATION_URL = 'https://github.com/ktdreyer/product-listings-manager'


class Index(Resource):
    def get(self):
        """ Link to the documentation and top-level API endpoints. """
        return {
            'documentation_url': DOCUMENTATION_URL,
            'xmlrpc_url': url_for('xmlrpc', _external=True),
            'api_v1_url': url_for('api_v1.index', _external=True),
        }


api = Api(blueprint)
api.add_resource(Index, '/')
