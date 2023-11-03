# SPDX-License-Identifier: GPL-2.0+
from typing import Any

from pydantic import BaseModel, Field

SQL_QUERY_EXAMPLES = {
    "SELECT": {
        "summary": "List variant, allow_source_only for a product",
        "value": {
            "query": (
                "SELECT variant, allow_source_only"
                " FROM products WHERE label = :label LIMIT 1"
            ),
            "params": {
                "label": "RHEL-8.2.0.GA",
            },
        },
    },
    "SELECT_LIST_CHECK": {
        "summary": "SELECT with ARRAY placeholders",
        "value": {
            "query": (
                "SELECT * FROM tree_packages"
                " WHERE trees_id = ANY(:tree_ids)"
                " AND packages_id = ANY(:package_ids)"
            ),
            "params": {
                "tree_ids": [1, 2, 3],
                "package_ids": [10, 20],
            },
        },
    },
    "INSERT": {
        "summary": "Insert a new product",
        "value": {
            "query": (
                "INSERT INTO products (id, label, version, variant, allow_source_only)"
                " VALUES (nextval('products_id_seq'), :label, :version, :variant,"
                " :allow_source_only)"
                " RETURNING id"
            ),
            "params": {
                "label": "product1",
                "version": "1.2",
                "variant": "Client",
                "allow_source_only": 1,
            },
        },
    },
    "DELETE": {
        "summary": "Delete a product",
        "value": {
            "query": (
                "DELETE FROM products"
                " WHERE label = :label AND version = :version AND variant = :variant"
            ),
            "params": {
                "label": "product1",
                "version": "1.2",
                "variant": "Client",
            },
        },
    },
}


class Message(BaseModel):
    message: str


class LoginInfo(BaseModel):
    user: str
    groups: list[str]


class Permission(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    contact: str | None = None
    users: list[str] = []
    groups: list[str] = []
    queries: list[str] = []


class SqlQuery(BaseModel):
    query: str = Field(min_length=1)
    params: dict[str, Any] = {}

    model_config = {
        "json_schema_extra": {
            "examples": [x["value"] for x in SQL_QUERY_EXAMPLES.values()]
        }
    }

    def __repr__(self):
        return f"<SqlQuery: {self.query!r} | {self.params!r}>"
