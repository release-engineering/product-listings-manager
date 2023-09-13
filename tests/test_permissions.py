# SPDX-License-Identifier: GPL-2.0+
from product_listings_manager.config import load_config_from_env

from .conftest import PERMISSIONS


class TestPermissions:
    def test_get_permissions_default_is_empty(self, client):
        r = client.get("/api/v1.0/permissions")
        assert r.status_code == 200, r.text
        assert r.json == []

    def test_get_permissions_without_filename(self, client, monkeypatch):
        monkeypatch.setenv("PLM_PERMISSIONS", "")
        load_config_from_env(client.application)
        r = client.get("/api/v1.0/permissions")
        assert r.status_code == 200, r.text
        assert r.json == []

    def test_get_permissions(self, auth_client):
        r = auth_client.get("/api/v1.0/permissions")
        assert r.status_code == 200, r.text
        assert r.json == PERMISSIONS
