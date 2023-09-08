import base64
import json
from unittest.mock import ANY, patch

from gssapi.exceptions import GSSError
from ldap import SERVER_DOWN, LDAPError
from pytest import fixture, mark

from product_listings_manager.config import load_config_from_env

from .factories import ProductsFactory

LDAP_HOST = "ldap://ldap.example.com"
LDAP_BASE = "ou=Groups,dc=example,dc=com"
LDAP_SEARCH = "(memberUid=test_user)"
PERMISSIONS = [
    {
        "name": "test user permission",
        "users": ["test_user"],
        "queries": ["INSERT *", "ROLLBACK"],
    },
    {
        "name": "test group1 permission",
        "groups": ["group1"],
        "queries": ["SELECT *"],
    },
    {
        "name": "test group2 permission",
        "groups": ["group2"],
        "queries": ["DELETE *"],
    },
]


def auth_headers():
    token = base64.b64encode(b"SECRET").decode("utf-8")
    return {"Authorization": f"Negotiate {token}"}


@fixture
def auth_client(client, monkeypatch, tmp_path):
    ldap_searches = [{"BASE": LDAP_BASE, "SEARCH_STRING": LDAP_SEARCH}]
    monkeypatch.setenv("PLM_LDAP_HOST", "ldap://ldap.example.com")
    monkeypatch.setenv("PLM_LDAP_SEARCHES", json.dumps(ldap_searches))

    permissions_file = tmp_path / "permissions.json"
    with open(permissions_file, "w") as f:
        json.dump(PERMISSIONS, f)
    monkeypatch.setenv("PLM_PERMISSIONS", str(permissions_file))

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
        r = auth_client.get("/api/v1.0/login", headers=auth_headers())
        assert r.status_code == 403, r.text
        assert r.json == {"message": "Attempted multiple GSSAPI round trips"}

    def test_login_gssapi_error(self, auth_client, gssapi_context):
        gssapi_context().step.side_effect = GSSError(1, 2)
        r = auth_client.get("/api/v1.0/login", headers=auth_headers())
        assert r.status_code == 403, r.text
        assert r.json == {"message": "Authentication failed"}

    def test_login(self, auth_client, gssapi_context, ldap_connection):
        r = auth_client.get("/api/v1.0/login", headers=auth_headers())
        assert r.status_code == 200, r.text
        assert r.json == {"user": "test_user", "groups": ["group1"]}
        ldap_connection.search_s.assert_called_once_with(
            LDAP_BASE, ANY, LDAP_SEARCH, ANY
        )

    def test_login_ldap_down(
        self, auth_client, gssapi_context, ldap_connection
    ):
        ldap_connection.search_s.side_effect = SERVER_DOWN
        r = auth_client.get("/api/v1.0/login", headers=auth_headers())
        assert r.status_code == 502, r.text
        assert r.json == {"message": "The LDAP server is unreachable"}

    def test_login_ldap_error(
        self, auth_client, gssapi_context, ldap_connection
    ):
        ldap_connection.search_s.side_effect = LDAPError
        r = auth_client.get("/api/v1.0/login", headers=auth_headers())
        assert r.status_code == 502, r.text
        assert r.json == {"message": "Unexpected LDAP connection error"}


class TestPermissions:
    def test_get_permissions_default_is_empty(self, client):
        r = client.get("/api/v1.0/permissions")
        assert r.status_code == 200, r.text
        assert r.json == []

    def test_get_permissions(self, auth_client):
        r = auth_client.get("/api/v1.0/permissions")
        assert r.status_code == 200, r.text
        assert r.json == PERMISSIONS


class TestDBQuery:
    @mark.parametrize(
        "input",
        (
            {},
            {"query": []},
            [],
            "",
            {"query": "SELECT * FROM products", "params": []},
            0,
        ),
    )
    def test_db_query_bad_params(
        self, auth_client, gssapi_context, ldap_connection, input
    ):
        r = auth_client.post(
            "/api/v1.0/dbquery", json=input, headers=auth_headers()
        )
        assert r.status_code == 400, r.text
        assert r.json == {"message": ANY}
        assert r.json["message"].startswith(
            "Parameter must have the following format"
        )

    def test_db_query_unauthorized(
        self, auth_client, gssapi_context, ldap_connection
    ):
        query = "DELETE FROM products"
        r = auth_client.post(
            "/api/v1.0/dbquery", json=query, headers=auth_headers()
        )
        assert r.status_code == 401, r.text
        assert r.json == {
            "message": "User test_user is not authorized to use this query"
        }

    def test_db_query_unauthorized_multiple_queries(
        self, auth_client, gssapi_context, ldap_connection
    ):
        queries = ["SELECT * FROM products;", "DELETE FROM products"]
        r = auth_client.post(
            "/api/v1.0/dbquery", json=queries, headers=auth_headers()
        )
        assert r.status_code == 401, r.text
        assert r.json == {
            "message": "User test_user is not authorized to use this query"
        }

    def test_db_query_unauthorized_no_matching_groups(
        self, auth_client, gssapi_context, ldap_connection
    ):
        query = "SELECT * FROM products"
        auth_client.application.config["PERMISSIONS"] = []
        r = auth_client.post(
            "/api/v1.0/dbquery", json=query, headers=auth_headers()
        )
        assert r.status_code == 401, r.text

    def test_db_query_select_bad(
        self, auth_client, gssapi_context, ldap_connection
    ):
        query = "SELECT * FROM bad_table"
        r = auth_client.post(
            "/api/v1.0/dbquery", json={"query": query}, headers=auth_headers()
        )
        assert r.status_code == 400, r.text
        assert r.json == {"message": ANY}
        assert r.json["message"].startswith("DB query failed: ")

    @mark.parametrize(
        "query",
        (
            "SELECT id, label, version, variant FROM products",
            # SQL is case-insensitive
            "select ID, LABEL, VERSION, VARIANT from PRODUCTS",
            "select id, label, version, variant from products",
        ),
    )
    def test_db_query_select(
        self, auth_client, gssapi_context, ldap_connection, query
    ):
        p1 = ProductsFactory(label="product1", version="1.2", variant="Client")
        p2 = ProductsFactory(label="product2", version="1.2", variant="Server")
        r = auth_client.post(
            "/api/v1.0/dbquery", json={"query": query}, headers=auth_headers()
        )
        assert r.status_code == 200, r.text
        assert r.json == [
            [p1.id, "product1", "1.2", "Client"],
            [p2.id, "product2", "1.2", "Server"],
        ]

    def test_db_query_insert(
        self, auth_client, gssapi_context, ldap_connection
    ):
        queries = [
            {
                "query": (
                    "INSERT INTO products (label, version, variant, allow_source_only)"
                    "  VALUES (:label, :version, :variant, :allow_source_only)"
                ),
                "params": {
                    "label": "product1",
                    "version": "1.2",
                    "variant": "Client",
                    "allow_source_only": 1,
                },
            },
            [
                "SELECT label, version, variant, allow_source_only FROM products"
            ],
        ]
        for query in queries:
            r = auth_client.post(
                "/api/v1.0/dbquery",
                json=query,
                headers=auth_headers(),
            )
            assert r.status_code == 200, r.text

        assert r.json == [["product1", "1.2", "Client", 1]]

    def test_db_query_insert_with_select(
        self, auth_client, gssapi_context, ldap_connection
    ):
        queries = [
            {
                "query": (
                    "INSERT INTO products (label, version, variant, allow_source_only)"
                    "  VALUES (:label, :version, :variant, :allow_source_only)"
                ),
                "params": {
                    "label": "product1",
                    "version": "1.2",
                    "variant": "Client",
                    "allow_source_only": 1,
                },
            },
            "SELECT label, version, variant, allow_source_only FROM products",
        ]
        r = auth_client.post(
            "/api/v1.0/dbquery",
            json=queries,
            headers=auth_headers(),
        )
        assert r.status_code == 200, r.text
        assert r.json == [["product1", "1.2", "Client", 1]]

    def test_db_query_insert_with_rollback(
        self, auth_client, gssapi_context, ldap_connection
    ):
        queries = [
            {
                "query": (
                    "INSERT INTO products (label, version, variant, allow_source_only)"
                    "  VALUES (:label, :version, :variant, :allow_source_only)"
                ),
                "params": {
                    "label": "product1",
                    "version": "1.2",
                    "variant": "Client",
                    "allow_source_only": 1,
                },
            },
            "ROLLBACK",
            "SELECT label, version, variant, allow_source_only FROM products",
        ]
        r = auth_client.post(
            "/api/v1.0/dbquery",
            json=queries,
            headers=auth_headers(),
        )
        assert r.status_code == 200, r.text
        assert r.json == []

    def test_db_query_rollback_after_failure(
        self, auth_client, gssapi_context, ldap_connection
    ):
        queries = [
            "INSERT INTO products (label, version, variant, allow_source_only)"
            "  VALUES ('product1', '1.2', 'Client', 1)",
            "INSERT INTO products (label, version, variant, allow_source_only)"
            "  VALUES ('product1', null, 'Client', 1)",
        ]
        r = auth_client.post(
            "/api/v1.0/dbquery",
            json=queries,
            headers=auth_headers(),
        )
        assert r.status_code == 400, r.text
        assert r.json == {"message": ANY}
        assert r.json["message"].startswith("DB query failed: ")
        assert "('product1', null, 'Client', 1)" in r.json["message"]
        assert "NOT NULL constraint failed" in r.json["message"]

        r = auth_client.post(
            "/api/v1.0/dbquery",
            json="SELECT label, version, variant, allow_source_only FROM products",
            headers=auth_headers(),
        )
        assert r.status_code == 200, r.text
        assert r.json == []
