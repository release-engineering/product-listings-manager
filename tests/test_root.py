# SPDX-License-Identifier: GPL-2.0+
class TestRoot:
    def test_get_version(self, client):
        r = client.get("/")
        expected_docs = (
            "https://github.com/release-engineering/product-listings-manager"
        )
        expected_json = {
            "api_v1_url": "http://testserver/api/v1.0/",
            "documentation_url": expected_docs,
            "api_reference": "http://testserver/redoc",
            "swagger_ui": "http://testserver/docs",
        }
        assert r.status_code == 200
        assert r.json() == expected_json
