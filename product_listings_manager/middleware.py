# SPDX-License-Identifier: GPL-2.0+
import re

from starlette.datastructures import URL
from starlette.responses import RedirectResponse
from starlette.types import ASGIApp, Receive, Scope, Send

repeated_quotes = re.compile(r"//+")


class UrlRedirectMiddleware:
    """
    Redirects an URL with repeated slashes to an URL with single slashes.

    See the original: https://github.com/tiangolo/fastapi/discussions/7312
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        url = URL(scope=scope)
        if "//" in url.path:
            url = url.replace(path=repeated_quotes.sub("/", url.path))
            response = RedirectResponse(url, status_code=307)
            await response(scope, receive, send)
        else:
            await self.app(scope, receive, send)
