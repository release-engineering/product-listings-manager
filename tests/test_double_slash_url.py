class TestDoubleSlashURL(object):
    def test_double_slash_url(self, client):
        r = client.get("/api//v1.0/", follow_redirects=True)
        assert r.status_code == 200
        assert len(r.history) == 1
        assert r.request.path == "/api/v1.0/"
