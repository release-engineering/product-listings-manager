# SPDX-License-Identifier: GPL-2.0+
"""Helper function for managing raw SQL queries"""
import logging
from typing import Any

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import ResourceClosedError, SQLAlchemyError

DB_QUERY_PARAM_ERROR = (
    'Parameter must have the following format ("params" is optional): '
    '[{"query": QUERY_STRING, "params": {PARAMETER_NAME: PARAMETER_STRING_VALUE}...]'
)

logger = logging.getLogger(__name__)


def queries_from_user_input(input: Any) -> list[Any]:
    if isinstance(input, dict):
        return [input]

    if isinstance(input, str):
        return [{"query": input}]

    if isinstance(input, list):
        return [q if isinstance(q, dict) else {"query": q} for q in input]

    raise HTTPException(status_code=400, detail=DB_QUERY_PARAM_ERROR)


def validate_queries(queries: list[dict[Any, Any]]):
    if not queries:
        raise HTTPException(status_code=400, detail=DB_QUERY_PARAM_ERROR)

    for query in queries:
        query_text = query.get("query")
        if not query_text or not isinstance(query_text, str):
            raise HTTPException(status_code=400, detail=DB_QUERY_PARAM_ERROR)

        params = query.get("params")
        if params is not None and not isinstance(params, dict):
            raise HTTPException(status_code=400, detail=DB_QUERY_PARAM_ERROR)


def execute_queries(db, queries: list[dict[str, str]]) -> list[list[Any]]:
    with db.begin():
        for query in queries:
            query_text = query.get("query")
            params = query.get("params")
            try:
                result = db.execute(text(query_text), params=params)
            except SQLAlchemyError as e:
                logger.warning("Failed DB query for user %s", e)
                raise HTTPException(
                    status_code=400, detail=f"DB query failed: {e}"
                )

        db.commit()

    try:
        return [list(row) for row in result]
    except ResourceClosedError:
        return []
