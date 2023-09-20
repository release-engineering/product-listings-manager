# SPDX-License-Identifier: GPL-2.0+
from pytest import raises

from .conftest import PERMISSIONS


class TestPermissions:
    def test_get_permissions_default_is_empty(self, client):
        r = client.get("/api/v1.0/permissions")
        assert r.status_code == 200, r.text
        assert r.json() == []

    def test_get_permissions_without_filename(self, client, monkeypatch):
        monkeypatch.setenv("PLM_PERMISSIONS", "")
        r = client.get("/api/v1.0/permissions")
        assert r.status_code == 200, r.text
        assert r.json() == []

    def test_get_permissions(self, auth_client):
        r = auth_client.get("/api/v1.0/permissions")
        assert r.status_code == 200, r.text
        # drop optional default values
        permissions = [{k: v for k, v in p.items() if v} for p in r.json()]
        assert permissions == PERMISSIONS

    def test_get_permissions_with_invalid_config(
        self, auth_client, monkeypatch, tmp_path
    ):
        permissions_file = tmp_path / "permissions_bad.json"
        with open(permissions_file, "w") as f:
            f.write("[{}]")

        monkeypatch.setenv("PLM_PERMISSIONS", str(permissions_file))

        with raises(ValueError):
            auth_client.get("/api/v1.0/permissions")

    def test_get_permissions_with_missing_config(
        self, auth_client, monkeypatch, tmp_path
    ):
        permissions_file = tmp_path / "permissions_empty.json"
        monkeypatch.setenv("PLM_PERMISSIONS", str(permissions_file))

        with raises(FileNotFoundError):
            auth_client.get("/api/v1.0/permissions")
