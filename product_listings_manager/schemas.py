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
                    "params": {
                        "label": "RHEL-8.2.0.GA",
                    },
                    "query": (
                        "SELECT variant, allow_source_only"
                        "FROM products WHERE label = :label LIMIT 1"
                    ),
                },
            ]
        }
    }
