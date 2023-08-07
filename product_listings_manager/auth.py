# SPDX-License-Identifier: GPL-2.0+
import base64
import binascii

import gssapi
from flask import current_app, Response
from werkzeug.exceptions import Unauthorized, Forbidden


# Inspired by https://github.com/mkomitee/flask-kerberos/blob/master/flask_kerberos.py
# Later cleaned and ported to python-gssapi
def process_gssapi_request(token):
    try:
        stage = "initialize server context"
        sc = gssapi.SecurityContext(usage="accept")

        stage = "step context"
        token = sc.step(token if token else None)
        token = token if token is not None else ""

        # The current architecture cannot support continuation here
        stage = "checking completion"
        if not sc.complete:
            current_app.logger.error(
                "Multiple GSSAPI round trips not supported"
            )
            raise Forbidden("Attempted multiple GSSAPI round trips")

        current_app.logger.debug("Completed GSSAPI negotiation")

        stage = "getting remote user"
        user = str(sc.initiator_name)
        return user, token
    except gssapi.exceptions.GSSError as e:
        current_app.logger.exception(
            "Unable to authenticate: failed to %s: %s",
            stage,
            e.gen_message(),
        )
        raise Forbidden("Authentication failed")


def get_user(request):
    return get_user_by_method(request, "Kerberos")


def get_user_by_method(request, auth_method):
    if "Authorization" not in request.headers:
        response = Response(
            "Unauthorized", 401, {"WWW-Authenticate": "Negotiate"}
        )
        raise Unauthorized(response=response)

    header = request.headers.get("Authorization")
    scheme, *rest = header.strip().split(maxsplit=1)

    if scheme != "Negotiate":
        raise Unauthorized(
            "Unsupported authentication scheme; supported is Negotiate"
        )

    if not rest or not rest[0]:
        raise Unauthorized("Missing authentication token")

    token = rest[0]

    try:
        user, token = process_gssapi_request(base64.b64decode(token))
    except binascii.Error:
        raise Unauthorized("Invalid authentication token")

    token = base64.b64encode(token).decode("utf-8")
    headers = {"WWW-Authenticate": f"Negotiate {token}"}

    # remove realm
    user = user.split("@")[0]
    return user, headers
