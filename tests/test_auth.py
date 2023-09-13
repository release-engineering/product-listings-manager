# SPDX-License-Identifier: GPL-2.0+
import base64
from unittest.mock import ANY

from gssapi.exceptions import GSSError
from ldap import SERVER_DOWN, LDAPError
from pytest import mark

from .conftest import LDAP_BASE, LDAP_SEARCH, auth_headers


class TestLogin:
    def test_login_unconfigured(self, client):
        r = client.get("/api/v1.0/login")
        assert r.status_code == 500, r.text
        assert r.json == {
            "message": "Server configuration LDAP_HOST and LDAP_SEARCHES is required."
        }

    def test_login_no_auth_header(self, auth_client):
        r = auth_client.get("/api/v1.0/login")
        assert r.status_code == 401, r.text

    def test_login_invalid_token(self, auth_client):
        token = base64.b64encode(b"SECRET").decode("utf-8")
        headers = {"Authorization": f"Negotiate BAD {token}"}
        r = auth_client.get("/api/v1.0/login", headers=headers)
        assert r.status_code == 401, r.text
        assert r.json == {"message": "Invalid authentication token"}

    def test_login_unsuported_auth_scheme(self, auth_client):
        headers = {"Authorization": "Bearer SECRET"}
        r = auth_client.get("/api/v1.0/login", headers=headers)
        assert r.status_code == 401, r.text
        assert r.json == {
            "message": "Unsupported authentication scheme; supported is Negotiate",
        }

    @mark.parametrize("auth_header", ("Negotiate", "Negotiate "))
    def test_login_missing_token(self, auth_client, auth_header):
        headers = {"Authorization": auth_header}
        r = auth_client.get("/api/v1.0/login", headers=headers)
        assert r.status_code == 401, r.text
        assert r.json == {"message": "Missing authentication token"}

    def test_login_multiple_roundtrips(self, auth_client, gssapi_context):
        gssapi_context().complete = False
        r = auth_client.get("/api/v1.0/login", headers=auth_headers())
        assert r.status_code == 403, r.text
        assert r.json == {"message": "Attempted multiple GSSAPI round trips"}

    def test_login_gssapi_error(self, auth_client, gssapi_context):
        gssapi_context().step.side_effect = GSSError(1, 2)
        r = auth_client.get("/api/v1.0/login", headers=auth_headers())
        assert r.status_code == 403, r.text
        assert r.json == {"message": "Authentication failed"}

    def test_login(self, auth_client, ldap_connection):
        r = auth_client.get("/api/v1.0/login", headers=auth_headers())
        assert r.status_code == 200, r.text
        assert r.json == {"user": "test_user", "groups": ["group1"]}
        ldap_connection.search_s.assert_called_once_with(
            LDAP_BASE, ANY, LDAP_SEARCH, ANY
        )

    def test_login_ldap_down(self, auth_client, ldap_connection):
        ldap_connection.search_s.side_effect = SERVER_DOWN
        r = auth_client.get("/api/v1.0/login", headers=auth_headers())
        assert r.status_code == 502, r.text
        assert r.json == {"message": "The LDAP server is unreachable"}

    def test_login_ldap_error(self, auth_client, ldap_connection):
        ldap_connection.search_s.side_effect = LDAPError
        r = auth_client.get("/api/v1.0/login", headers=auth_headers())
        assert r.status_code == 502, r.text
        assert r.json == {"message": "Unexpected LDAP connection error"}
