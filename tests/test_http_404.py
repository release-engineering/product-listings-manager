class TestHttp404(object):
    def test_http_404(self, client):
        r = client.get("/nonexistent")
        assert r.status_code == 404
