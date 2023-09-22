# SPDX-License-Identifier: GPL-2.0+
import logging
from unittest.mock import ANY, patch

from pytest import mark

from .conftest import auth_headers
from .factories import ProductsFactory


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
    def test_db_query_bad_params(self, auth_client, input):
        r = auth_client.post(
            "/api/v1.0/dbquery", json=input, headers=auth_headers()
        )
        assert r.status_code == 422, r.text

    def test_db_query_unauthorized(self, auth_client):
        query = "DELETE FROM products"
        r = auth_client.post(
            "/api/v1.0/dbquery", json=query, headers=auth_headers()
        )
        assert r.status_code == 403, r.text
        assert r.json() == {
            "message": "User test_user is not authorized to use this query"
        }

    def test_db_query_unauthorized_multiple_queries(self, auth_client):
        queries = ["SELECT * FROM products;", "DELETE FROM products"]
        r = auth_client.post(
            "/api/v1.0/dbquery", json=queries, headers=auth_headers()
        )
        assert r.status_code == 403, r.text
        assert r.json() == {
            "message": "User test_user is not authorized to use this query"
        }

    def test_db_query_unauthorized_no_matching_groups(self, auth_client):
        query = "SELECT * FROM products"
        with patch(
            "product_listings_manager.rest_api_v1.parse_permissions",
            return_value=[],
        ):
            r = auth_client.post(
                "/api/v1.0/dbquery", json=query, headers=auth_headers()
            )
        assert r.status_code == 403, r.text

    def test_db_query_select_bad(self, auth_client):
        query = "SELECT * FROM bad_table"
        r = auth_client.post(
            "/api/v1.0/dbquery", json={"query": query}, headers=auth_headers()
        )
        assert r.status_code == 400, r.text
        assert r.json() == {"message": ANY}
        assert r.json()["message"].startswith("DB query failed: ")

    @mark.parametrize(
        "query",
        (
            "SELECT id, label, version, variant FROM products",
            # SQL is case-insensitive
            "select ID, LABEL, VERSION, VARIANT from PRODUCTS",
            "select id, label, version, variant from products",
            # multi-line and indentation
            """
            SELECT
              id, label, version, variant
                FROM products
            """,
        ),
    )
    def test_db_query_select(self, auth_client, query):
        p1 = ProductsFactory(label="product1", version="1.2", variant="Client")
        p2 = ProductsFactory(label="product2", version="2.3", variant="Server")
        r = auth_client.post(
            "/api/v1.0/dbquery", json={"query": query}, headers=auth_headers()
        )
        assert r.status_code == 200, r.text
        assert r.json() == [
            [p1.id, "product1", "1.2", "Client"],
            [p2.id, "product2", "2.3", "Server"],
        ]

    def test_db_query_insert(self, auth_client):
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

        assert r.json() == [["product1", "1.2", "Client", 1]]

    def test_db_query_insert_with_select(self, auth_client):
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
        assert r.json() == [["product1", "1.2", "Client", 1]]

    def test_db_query_insert_with_rollback(self, auth_client):
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
        assert r.json() == []

    def test_db_query_rollback_after_failure(self, auth_client):
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
        assert r.json() == {"message": ANY}
        assert r.json()["message"].startswith("DB query failed: ")
        assert "('product1', null, 'Client', 1)" in r.json()["message"]
        assert "NOT NULL constraint failed" in r.json()["message"]

        r = auth_client.post(
            "/api/v1.0/dbquery",
            json="SELECT label, version, variant, allow_source_only FROM products",
            headers=auth_headers(),
        )
        assert r.status_code == 200, r.text
        assert r.json() == []

    def test_db_query_logs_user_and_queries(self, auth_client, caplog):
        queries = [
            {
                "query": (
                    "INSERT INTO products (label, version, variant, allow_source_only)"
                    " VALUES (:label, :version, :variant, :allow_source_only)"
                ),
                "params": {
                    "label": f"product{x}",
                    "version": "1.2",
                    "variant": "Client",
                    "allow_source_only": 1,
                },
            }
            for x in range(2)
        ]
        with caplog.at_level(logging.INFO):
            r = auth_client.post(
                "/api/v1.0/dbquery",
                json=queries,
                headers=auth_headers(),
            )
        assert r.status_code == 200, r.text
        assert r.json() == []

        assert len(caplog.records) > 0
        assert (
            "Authorized DB queries for user test_user: ["
            f"<SqlQuery: {queries[0]['query']!r} | {queries[0]['params']!r}>, "
            f"<SqlQuery: {queries[1]['query']!r} | {queries[1]['params']!r}>]"
        ) == caplog.records[0].message
