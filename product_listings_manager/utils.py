# SPDX-License-Identifier: GPL-2.0+
import logging

from fastapi import Request

logger = logging.getLogger(__name__)


def log_remote_call_error(request: Request, label, *args, **kwargs):
    logger.exception(
        "%s: callee=%r, args=%r, kwargs=%r",
        label,
        request.client,
        args,
        kwargs,
    )
