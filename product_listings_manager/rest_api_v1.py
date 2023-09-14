# SPDX-License-Identifier: GPL-2.0+
import json
import logging
import os
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from product_listings_manager import __version__, products, utils
from product_listings_manager.auth import get_user
from product_listings_manager.authorization import LdapConfig, get_user_groups
from product_listings_manager.db_queries import execute_queries
from product_listings_manager.models import get_db
from product_listings_manager.permissions import has_permission
from product_listings_manager.schemas import (
    LoginInfo,
    Message,
    Permission,
    SqlQuery,
)

router = APIRouter(prefix="/api/v1.0")

logger = logging.getLogger(__name__)

HEALTH_OK_MESSAGE = "It works!"


def ldap_config() -> LdapConfig:
    ldap_host = os.getenv("PLM_LDAP_HOST")
    ldap_searches = json.loads(os.getenv("PLM_LDAP_SEARCHES", "[]"))

    if not ldap_host or not ldap_searches:
        raise HTTPException(
            status_code=500,
            detail="Server configuration LDAP_HOST and LDAP_SEARCHES is required.",
        )

    return LdapConfig(host=ldap_host, searches=ldap_searches)


@lru_cache
def parse_permissions(filename) -> list[Permission]:
    """
    Return PERMISSIONS configuration.
    """
    if not filename:
        return []

    with open(filename) as f:
        return [Permission.model_validate(x) for x in json.load(f)]


@router.get("/")
def api_index(request: Request):
    """Link to the the v1 API endpoints."""
    return {
        "about_url": str(request.url_for("about")),
        "health_url": str(request.url_for("health")),
        "product_info_url": str(
            request.url_for("product_info", label=":label")
        ),
        "product_labels_url": str(request.url_for("product_labels")),
        "product_listings_url": str(
            request.url_for(
                "product_listings",
                label=":label",
                build_info=":build_info",
            )
        ),
        "module_product_listings_url": str(
            request.url_for(
                "module_product_listings",
                label=":label",
                module_build_nvr=":module_build_nvr",
            )
        ),
    }


@router.get("/about")
def about():
    return {
        "source": "https://github.com/release-engineering/product-listings-manager",
        "version": __version__,
    }


@router.get(
    "/health",
    responses={
        200: {"model": Message(message=HEALTH_OK_MESSAGE)},
        503: {"model": Message},
    },
)
def health(db: Session = Depends(get_db)):
    """Provides status report"""

    try:
        permissions()
    except Exception as e:
        logger.error("Failed to parse permissions configuration: %s", e)
        raise HTTPException(
            status_code=503,
            detail=f"Failed to parse permissions configuration: {e}",
        )

    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as e:
        logger.warning("DB health check failed: %s", e)
        raise HTTPException(status_code=503, detail=f"DB Error: {e}")

    try:
        products.get_koji_session().getAPIVersion()
    except Exception as e:
        logger.warning("Koji health check failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Koji Error: {e}")

    return Message(message=HEALTH_OK_MESSAGE)


@router.get("/login")
def login(request: Request) -> LoginInfo:
    """Shows credentials for the current user."""
    ldap_config_ = ldap_config()
    user, headers = get_user(request)
    groups = set(get_user_groups(user, ldap_config_))

    return LoginInfo(user=user, groups=sorted(groups))


@router.get("/product-info/{label}")
def product_info(label: str, request: Request, db: Session = Depends(get_db)):
    try:
        versions, variants = products.get_product_info(db, label)
    except products.ProductListingsNotFoundError as ex:
        raise HTTPException(status_code=404, detail=str(ex))
    except Exception as ex:
        utils.log_remote_call_error(
            request, "API call get_product_info() failed", label
        )
        raise HTTPException(status_code=500, detail=str(ex))
    return [versions, variants]


@router.get("/product-labels")
def product_labels(request: Request, db: Session = Depends(get_db)):
    try:
        return products.get_product_labels(db)
    except Exception as ex:
        utils.log_remote_call_error(
            request, "API call get_product_labels() failed"
        )
        raise HTTPException(status_code=500, detail=str(ex))


@router.get("/product-listings/{label}/{build_info}")
def product_listings(
    label: str,
    build_info: str,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        return products.get_product_listings(db, label, build_info)
    except products.ProductListingsNotFoundError as ex:
        raise HTTPException(status_code=404, detail=str(ex))
    except Exception as ex:
        utils.log_remote_call_error(
            request,
            "API call get_product_listings() failed",
            label,
            build_info,
        )
        raise HTTPException(status_code=500, detail=str(ex))


@router.get("/module-product-listings/{label}/{module_build_nvr}")
def module_product_listings(
    label: str,
    module_build_nvr: str,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        return products.get_module_product_listings(
            db, label, module_build_nvr
        )
    except products.ProductListingsNotFoundError as ex:
        raise HTTPException(status_code=404, detail=str(ex))
    except Exception as ex:
        utils.log_remote_call_error(
            request,
            "API call get_module_product_listings() failed",
            label,
            module_build_nvr,
        )
        raise HTTPException(status_code=500, detail=str(ex))


@router.get("/permissions")
def permissions() -> list[Permission]:
    """
    Lists user and group permissions for using **dbquery** API.
    """
    filename = os.getenv("PLM_PERMISSIONS")
    return parse_permissions(filename)


@router.post("/dbquery")
async def dbquery(
    query_or_queries: SqlQuery | list[SqlQuery | str] | str,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Executes given SQL queries with optionally provided parameters.

    Multiple queries can be provided (pass as an array) but only the result
    (listed rows) from the last query will be returned.

    User must be logged in and have permission to execute the queries.
    """
    if not query_or_queries:
        raise HTTPException(
            status_code=422, detail="Queries must not be empty"
        )

    ldap_config_ = ldap_config()
    user, headers = get_user(request)

    # normalize queries type to list of SqlQuery
    if isinstance(query_or_queries, SqlQuery):
        queries = [query_or_queries]
    elif isinstance(query_or_queries, str):
        queries = [SqlQuery(query=query_or_queries)]
    elif isinstance(query_or_queries, list):
        queries = [
            q if isinstance(q, SqlQuery) else SqlQuery(query=q)
            for q in query_or_queries
        ]

    if not has_permission(user, queries, permissions(), ldap_config_):
        logger.warning("Unauthorized access for user %s", user)
        raise HTTPException(
            status_code=401,
            detail=f"User {user} is not authorized to use this query",
        )

    logger.info("Authorized access for user %s; input: %s", user, input)

    return execute_queries(db, queries)
