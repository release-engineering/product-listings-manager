import pytest

from mock import patch

from product_listings_manager.app import create_app
from product_listings_manager import products


@pytest.yield_fixture
def client():
    client = create_app().test_client()
    yield client


class TestIndex(object):
    def test_get_index(self, client):
        r = client.get('/api/v1.0/')
        expected_json = {
            'about_url': 'http://localhost/api/v1.0/about',
            'module_product_listings_url': 'http://localhost/api/v1.0/module-product-listings/:label/:module_build_nvr',
            'product_info_url': 'http://localhost/api/v1.0/product-info/:label',
            'product_listings_url': 'http://localhost/api/v1.0/product-listings/:label/:build_info',
        }
        assert r.status_code == 200
        assert r.get_json() == expected_json


class TestAbout(object):
    def test_get_version(self, client):
        from product_listings_manager import __version__
        r = client.get('/api/v1.0/about')
        assert r.status_code == 200
        assert r.get_json() == {'version': __version__}


class TestProductInfo(object):
    product_label = 'RHEL-6-Server-EXTRAS-6'
    product_info_data = ['6.9', ['EXTRAS-6']]

    @patch('product_listings_manager.products.getProductInfo', return_value=product_info_data)
    def test_get_product_info(self, mock_get_product_info, client):
        path = '/api/v1.0/product-info/{0}'.format(self.product_label)
        r = client.get(path)
        assert r.status_code == 200
        assert r.get_json() == mock_get_product_info.return_value


class TestProductListings(object):
    product_label = 'RHEL-6-Server-EXTRAS-6'
    nvr = 'dumb-init-1.2.0-1.20170802gitd283f8a.el6'
    product_listings_data = {
        'EXTRAS-6': {
            nvr: {
                'src': ['x86_64'], 'x86_64': ['x86_64']
            }
        }
    }

    @patch('product_listings_manager.products.getProductListings', return_value=product_listings_data)
    def test_get_product_listings(self, mock_get_product_listings, client):
        path = '/api/v1.0/product-listings/{0}/{1}'.format(self.product_label, self.nvr)
        r = client.get(path)
        assert r.status_code == 200
        assert r.get_json() == mock_get_product_listings.return_value

    @patch('product_listings_manager.products.getProductListings')
    def test_product_listings_not_found(self, mock_get_product_listings, client):
        error_message = 'NOT FOUND'
        mock_get_product_listings.side_effect = products.ProductListingsNotFoundError(error_message)
        path = '/api/v1.0/product-listings/{0}/{1}'.format(self.product_label, self.nvr)
        r = client.get(path)
        assert r.status_code == 404
        assert r.get_json() == {'message': error_message}


class TestModuleProductListings(object):
    product_label = 'RHEL-8.0.0'
    nvr = 'ruby-2.5-820181217154935.9edba152'
    product_listings_data = {
        'AppStream-8.0.0': ['x86_64']
    }

    @patch('product_listings_manager.products.getModuleProductListings', return_value=product_listings_data)
    def test_get_module_product_listings(self, mock_get_module_product_listings, client):
        path = '/api/v1.0/module-product-listings/{0}/{1}'.format(self.product_label, self.nvr)
        r = client.get(path)
        assert r.status_code == 200
        assert r.get_json() == mock_get_module_product_listings.return_value

    @patch('product_listings_manager.products.getModuleProductListings')
    def test_product_listings_not_found(self, mock_get_module_product_listings, client):
        error_message = 'NOT FOUND'
        mock_get_module_product_listings.side_effect = products.ProductListingsNotFoundError(error_message)
        path = '/api/v1.0/module-product-listings/{0}/{1}'.format(self.product_label, self.nvr)
        r = client.get(path)
        assert r.status_code == 404
        assert error_message in r.get_json().get('message', '')
