# SPDX-License-Identifier: GPL-2.0+
import json
import logging
import os
from functools import lru_cache
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from product_listings_manager import __version__, products, utils
from product_listings_manager.auth import get_user
from product_listings_manager.authorization import LdapConfig, get_user_groups
from product_listings_manager.db_queries import (
    execute_queries,
    queries_from_user_input,
    validate_queries,
)
from product_listings_manager.models import get_db
from product_listings_manager.permissions import has_permission

router = APIRouter(prefix="/api/v1.0")

logger = logging.getLogger(__name__)


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
def parse_permissions(filename) -> list[dict[str, Any]]:
    """
    Return PERMISSIONS configuration.
    """
    if not filename:
        return []

    with open(filename) as f:
        return json.load(f)


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


@router.get("/health")
def health(db: Session = Depends(get_db)):
    """Provides status report

    * 200 if everything is ok
    * 503 if service is not working as expected
    """

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

    return {"message": "It works!"}


@router.get("/login")
def login(request: Request):
    ldap_config_ = ldap_config()
    user, headers = get_user(request)
    groups = set(get_user_groups(user, ldap_config_))

    return {
        "user": user,
        "groups": sorted(groups),
    }


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
def permissions():
    filename = os.getenv("PLM_PERMISSIONS")
    return parse_permissions(filename)


@router.post("/dbquery")
async def dbquery(request: Request, db: Session = Depends(get_db)):
    input = request.json()
    ldap_config_ = ldap_config()
    user, headers = get_user(request)
    queries = queries_from_user_input(await input)
    validate_queries(queries)

    filename = os.getenv("PLM_PERMISSIONS")
    if not has_permission(
        user, queries, parse_permissions(filename), ldap_config_
    ):
        logger.warning("Unauthorized access for user %s", user)
        raise HTTPException(
            status_code=401,
            detail=f"User {user} is not authorized to use this query",
        )

    logger.info("Authorized access for user %s; input: %s", user, input)

    return execute_queries(db, queries)
