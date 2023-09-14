# SPDX-License-Identifier: GPL-2.0+
from typing import Any

from pydantic import BaseModel, Field


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
            "examples": [
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
                {
                    "query": (
                        "SELECT label, version, variant, allow_source_only"
                        "FROM products LIMIT 1"
                    ),
                },
            ]
        }
    }
