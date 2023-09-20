# SPDX-License-Identifier: GPL-2.0+
from fastapi import APIRouter, Request

router = APIRouter()

DOCUMENTATION_URL = (
    "https://github.com/release-engineering/product-listings-manager"
)


@router.get("/")
def index(request: Request):
    """Link to the documentation and top-level API endpoints."""
    return {
        "documentation_url": DOCUMENTATION_URL,
        "api_reference": str(request.url_for("redoc_html")),
        "swagger_ui": str(request.url_for("swagger_ui_html")),
        "api_v1_url": str(request.url_for("api_index")),
    }
