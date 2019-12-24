import logging
import sys


def init_logging(app):
    log_level = logging.DEBUG if app.debug else logging.INFO
    plm_logger = logging.getLogger("product_listings_manager")
    plm_logger.setLevel(log_level)

    fmt = "%(asctime)s %(levelname)s %(name)s %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setLevel(log_level)
    stream_handler.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))
    plm_logger.addHandler(stream_handler)
