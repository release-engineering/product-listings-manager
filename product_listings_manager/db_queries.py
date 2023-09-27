# SPDX-License-Identifier: GPL-2.0+
"""Helper function for managing raw SQL queries"""
import logging
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import ResourceClosedError, SQLAlchemyError

from product_listings_manager.schemas import SqlQuery

logger = logging.getLogger(__name__)


def execute_queries(db, queries: list[SqlQuery]) -> list[dict[str, Any]]:
    for query in queries:
        query_text = query.query
        params = query.params
        try:
            result = db.execute(text(query_text), params=params)

            # Always fetch the result to avoid "SQL statements in progress" error.
            try:
                rows = [dict(row._mapping) for row in result]
            except ResourceClosedError:
                rows = []
        except SQLAlchemyError as e:
            logger.warning("DB query failed: %s", e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"DB query failed: {e}",
            )

    db.commit()
    return rows
