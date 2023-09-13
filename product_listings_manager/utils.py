# SPDX-License-Identifier: GPL-2.0+
import traceback

from flask import current_app, request


def log_remote_call_error(label, *a, **kw):
    err = traceback.print_exc()
    callee = request.remote_addr
    current_app.logger.error(
        "%s: callee=%r, args=%r, kwargs=%r, %s", label, callee, a, kw, err
    )
