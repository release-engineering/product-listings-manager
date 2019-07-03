import pytest

from product_listings_manager.app import create_app


@pytest.yield_fixture
def client():
    client = create_app().test_client()
    yield client


class TestHttp404(object):
    def test_http_404(self, client):
        r = client.get('/nonexistent')
        assert r.status_code == 404
