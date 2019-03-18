import pytest

from product_listings_manager.app import create_app


@pytest.yield_fixture
def client():
    client = create_app().test_client()
    yield client


class TestRoot(object):
    def test_get_version(self, client):
        r = client.get('/')
        expected_docs = 'https://github.com/release-engineering/product-listings-manager'
        expected_json = {
            'api_v1_url': 'http://localhost/api/v1.0/',
            'documentation_url': expected_docs,
            'xmlrpc_url': 'http://localhost/xmlrpc',
        }
        assert r.status_code == 200
        assert r.get_json() == expected_json
