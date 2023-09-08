# SPDX-License-Identifier: GPL-2.0+
"""Helper function for managing raw SQL queries"""
from typing import Any

from flask import current_app
from sqlalchemy.exc import ResourceClosedError, SQLAlchemyError
from werkzeug.exceptions import BadRequest

from product_listings_manager.models import db

DB_QUERY_PARAM_ERROR = (
    'Parameter must have the following format ("params" is optional): '
    '[{"query": QUERY_STRING, "params": {PARAMETER_NAME: PARAMETER_STRING_VALUE}...]'
)


def queries_from_user_input(input: Any) -> list[Any]:
    if isinstance(input, dict):
        return [input]

    if isinstance(input, str):
        return [{"query": input}]

    if isinstance(input, list):
        return [q if isinstance(q, dict) else {"query": q} for q in input]

    raise BadRequest(DB_QUERY_PARAM_ERROR)


def validate_queries(queries: list[dict[Any, Any]]):
    if not queries:
        raise BadRequest(DB_QUERY_PARAM_ERROR)

    for query in queries:
        query_text = query.get("query")
        if not query_text or not isinstance(query_text, str):
            raise BadRequest(DB_QUERY_PARAM_ERROR)

        params = query.get("params")
        if params is not None and not isinstance(params, dict):
            raise BadRequest(DB_QUERY_PARAM_ERROR)


def execute_queries(queries: list[dict[str, str]]) -> list[list[Any]]:
    with db.session.begin():
        for query in queries:
            query_text = query.get("query")
            params = query.get("params")
            try:
                result = db.session.execute(db.text(query_text), params=params)
            except SQLAlchemyError as e:
                current_app.logger.warning("Failed DB query for user %s", e)
                raise BadRequest(f"DB query failed: {e}")

        db.session.commit()

    try:
        return [list(row) for row in result]
    except ResourceClosedError:
        return []
