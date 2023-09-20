# SPDX-License-Identifier: GPL-2.0+
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from product_listings_manager import rest_api_v1, root
from product_listings_manager.logger import init_logging
from product_listings_manager.middleware import UrlRedirectMiddleware


async def http_exception_handler(request, exc):
    return JSONResponse(
        {"message": exc.detail},
        status_code=exc.status_code,
        headers=exc.headers,
    )


def create_app():
    app = FastAPI()
    init_logging(app)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_middleware(UrlRedirectMiddleware)
    app.include_router(root.router)
    app.include_router(rest_api_v1.router)
    return app
