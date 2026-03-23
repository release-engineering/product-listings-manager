# SPDX-License-Identifier: GPL-2.0+
from unittest.mock import Mock, patch

from pytest import raises

from product_listings_manager.permissions import has_permission
from product_listings_manager.schemas import Permission, SqlQuery

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

    def test_has_permissions(self):
        ldap_config = Mock()
        user = "alice"
        permission = Permission(
            name="test", users=[user], queries=["INSERT * TO products"]
        )
        assert (
            has_permission(
                user,
                [SqlQuery(query="INSERT 1 to products")],
                [permission],
                ldap_config=ldap_config,
            )
            is True
        )
        assert (
            has_permission(
                user,
                [SqlQuery(query=" INSERT 1 to products ; ")],
                [permission],
                ldap_config=ldap_config,
            )
            is True
        )
        assert (
            has_permission(
                user,
                [SqlQuery(query="INSERT 1 to products2")],
                [permission],
                ldap_config=ldap_config,
            )
            is False
        )

    def test_has_permissions_oidc_groups_match(self):
        """OIDC groups match — authorized without LDAP."""
        ldap_config = Mock()
        user = "bob"
        permission = Permission(name="test", groups=["group1"], queries=["SELECT *"])
        assert (
            has_permission(
                user,
                [SqlQuery(query="SELECT 1")],
                [permission],
                ldap_config=ldap_config,
                oidc_groups=["group1"],
            )
            is True
        )

    def test_has_permissions_oidc_groups_no_match_ldap_fallback(self):
        """OIDC groups don't match, LDAP fallback authorizes."""
        ldap_config = Mock()
        user = "bob"
        permission = Permission(name="test", groups=["group1"], queries=["SELECT *"])
        with patch(
            "product_listings_manager.permissions.get_user_groups",
            return_value=["group1"],
        ):
            assert (
                has_permission(
                    user,
                    [SqlQuery(query="SELECT 1")],
                    [permission],
                    ldap_config=ldap_config,
                    oidc_groups=["wrong_group"],
                )
                is True
            )

    def test_has_permissions_oidc_groups_none_uses_ldap(self):
        """oidc_groups=None preserves existing LDAP-only behavior."""
        ldap_config = Mock()
        user = "bob"
        permission = Permission(name="test", groups=["group1"], queries=["SELECT *"])
        with patch(
            "product_listings_manager.permissions.get_user_groups",
            return_value=["group1"],
        ):
            assert (
                has_permission(
                    user,
                    [SqlQuery(query="SELECT 1")],
                    [permission],
                    ldap_config=ldap_config,
                    oidc_groups=None,
                )
                is True
            )
