# SPDX-License-Identifier: GPL-2.0+
"""
Health check endpoints for Kubernetes/OpenShift probes.

Separate endpoints for different probe types:
- /api/v1.0/health/live: Liveness probe - minimal check
- /api/v1.0/health/ready: Readiness/Startup probe - critical dependencies only (no Koji)
- /api/v1.0/health: Detailed health - all dependencies for monitoring
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from product_listings_manager.models import get_db
from product_listings_manager.schemas import HealthStatus, Message

router = APIRouter(prefix="/api/v1.0/health")

logger = logging.getLogger(__name__)


@router.get(
    "/live",
    responses={
        200: {"model": HealthStatus},
    },
)
def liveness():
    """
    Liveness probe endpoint.

    Checks only if the application process is alive and can handle requests.
    Does not check external dependencies.

    Used by Kubernetes liveness probe to determine if pod should be restarted.
    """
    return HealthStatus()


@router.get(
    "/ready",
    responses={
        200: {"model": HealthStatus},
        503: {"model": Message},
    },
)
def readiness(
    db: Annotated[Session, Depends(get_db)],
):
    """
    Readiness probe endpoint.

    Checks if the application can serve traffic by verifying:
    - Database connectivity (pod-specific, critical dependency)

    Does NOT check:
    - Permissions configuration (loaded at startup, app won't start if invalid)
    - External shared services like Koji/Brew (to avoid cascading failures
      where all pods become unready when a shared service is down)

    Used by Kubernetes readiness and startup probes to determine if
    pod should receive traffic.
    """
    # Check database connectivity
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as e:
        logger.warning("Database readiness check failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unavailable: {e}",
        )

    return HealthStatus()
