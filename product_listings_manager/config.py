"""PLM configuration module."""
import json
import os
from typing import Any


def read_json_file(filename: str):
    if not filename:
        return None

    with open(filename) as f:
        return json.load(f)


ENV_TO_CONFIG = (
    ("SQLALCHEMY_DATABASE_URI", lambda x: x),
    ("PLM_LDAP_HOST", lambda x: x),
    ("PLM_LDAP_SEARCHES", json.loads),
    ("PLM_PERMISSIONS", lambda x: read_json_file(x) or []),
)


class Config:
    """Default config."""

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_DATABASE_URI = "postgresql://user:pass@localhost/compose"

    LDAP_HOST: str = ""
    LDAP_SEARCHES: list[dict[str, str]] = []

    PERMISSIONS: list[dict[str, Any]] = []


class DevConfig(Config):
    """Development config."""

    SQLALCHEMY_ECHO = True


def load_config_from_env(app):
    # It's convenient to overwrite default config via env var in container.
    for env, transform in ENV_TO_CONFIG:
        key = env[4:] if env.startswith("PLM_") else env
        value = os.getenv(env)
        if value:
            app.config[key] = transform(value)


def load_config(app):
    app.config.from_object("product_listings_manager.config.Config")
    app.config.from_pyfile(
        "/etc/product-listings-manager/config.py", silent=True
    )

    if app.debug:
        app.config.from_object("product_listings_manager.config.DevConfig")

    app.config.from_envvar("PLM_CONFIG_FILE", silent=True)

    load_config_from_env(app)
