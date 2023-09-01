import base64
import json
from unittest.mock import ANY, patch

from gssapi.exceptions import GSSError
from ldap import SERVER_DOWN, LDAPError
from pytest import fixture, mark

from product_listings_manager.config import load_config_from_env

LDAP_HOST = "ldap://ldap.example.com"
LDAP_BASE = "ou=Groups,dc=example,dc=com"
LDAP_SEARCH = "(memberUid=test_user)"


@fixture
def auth_client(client, monkeypatch):
    ldap_searches = [{"BASE": LDAP_BASE, "SEARCH_STRING": LDAP_SEARCH}]
    monkeypatch.setenv("PLM_LDAP_HOST", "ldap://ldap.example.com")
    monkeypatch.setenv("PLM_LDAP_SEARCHES", json.dumps(ldap_searches))
    load_config_from_env(client.application)
    yield client


@fixture
def gssapi_context(client):
    with patch(
        "product_listings_manager.auth.gssapi.SecurityContext", autospec=True
    ) as context:
        context().initiator_name = "test_user@example.com"
        context().complete = True
        context().step.return_value = b"SECRET"
        yield context


@fixture
def ldap_connection(client):
    with patch("ldap.initialize", autospec=True) as ldap_init:
        ldap_connection = ldap_init(LDAP_HOST)
        ldap_connection.search_s.return_value = [
            ("ou=Groups,dc=example,dc=com", {"cn": [b"group1"]})
        ]
        yield ldap_connection


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
        token = base64.b64encode(b"SECRET").decode("utf-8")
        headers = {"Authorization": f"Negotiate {token}"}
        r = auth_client.get("/api/v1.0/login", headers=headers)
        assert r.status_code == 403, r.text
        assert r.json == {"message": "Attempted multiple GSSAPI round trips"}

    def test_login_gssapi_error(self, auth_client, gssapi_context):
        gssapi_context().step.side_effect = GSSError(1, 2)
        token = base64.b64encode(b"SECRET").decode("utf-8")
        headers = {"Authorization": f"Negotiate {token}"}
        r = auth_client.get("/api/v1.0/login", headers=headers)
        assert r.status_code == 403, r.text
        assert r.json == {"message": "Authentication failed"}

    def test_login(self, auth_client, gssapi_context, ldap_connection):
        token = base64.b64encode(b"SECRET").decode("utf-8")
        headers = {"Authorization": f"Negotiate {token}"}
        r = auth_client.get("/api/v1.0/login", headers=headers)
        assert r.status_code == 200, r.text
        assert r.json == {"user": "test_user", "groups": ["group1"]}
        ldap_connection.search_s.assert_called_once_with(
            LDAP_BASE, ANY, LDAP_SEARCH, ANY
        )

    def test_login_ldap_down(
        self, auth_client, gssapi_context, ldap_connection
    ):
        token = base64.b64encode(b"SECRET").decode("utf-8")
        headers = {"Authorization": f"Negotiate {token}"}
        ldap_connection.search_s.side_effect = SERVER_DOWN
        r = auth_client.get("/api/v1.0/login", headers=headers)
        assert r.status_code == 502, r.text
        assert r.json == {"message": "The LDAP server is unreachable"}

    def test_login_ldap_error(
        self, auth_client, gssapi_context, ldap_connection
    ):
        token = base64.b64encode(b"SECRET").decode("utf-8")
        headers = {"Authorization": f"Negotiate {token}"}
        ldap_connection.search_s.side_effect = LDAPError
        r = auth_client.get("/api/v1.0/login", headers=headers)
        assert r.status_code == 502, r.text
        assert r.json == {"message": "Unexpected LDAP connection error"}
