# SPDX-License-Identifier: GPL-2.0+
import base64
import json
import os
from unittest.mock import patch

from pytest import fixture, mark

from product_listings_manager.app import create_app
from product_listings_manager.config import load_config_from_env
from product_listings_manager.models import db

LDAP_HOST = "ldap://ldap.example.com"
LDAP_BASE = "ou=Groups,dc=example,dc=com"
LDAP_SEARCH = "(memberUid=test_user)"
PERMISSIONS = [
    {
        "name": "test user permission",
        "users": ["test_user"],
        "queries": ["INSERT *", "ROLLBACK"],
    },
    {
        "name": "test group1 permission",
        "groups": ["group1"],
        "queries": ["SELECT *"],
    },
    {
        "name": "test group2 permission",
        "groups": ["group2"],
        "queries": ["DELETE *"],
    },
]


def pytest_addoption(parser):
    parser.addoption(
        "--live",
        action="store_true",
        default=False,
        help="query live composedb and koji servers",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "live: mark test as requiring live composedb and koji servers",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--live"):
        return
    skip_live = mark.skip(
        reason="use --live argument to query production servers"
    )
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)


@fixture
def app():
    os.environ["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
    app = create_app()
    with app.app_context():
        db.create_all()
        yield app


@fixture
def client(app):
    client = app.test_client()
    yield client


@fixture
def gssapi_context(client):
    with patch(
        "product_listings_manager.auth.gssapi.SecurityContext", autospec=True
    ) as context:
        context().initiator_name = "test_user@example.com"
        context().complete = True
        context().step.return_value = b"SECRET"
        yield context


@fixture
def ldap_connection(client):
    with patch("ldap.initialize", autospec=True) as ldap_init:
        ldap_connection = ldap_init(LDAP_HOST)
        ldap_connection.search_s.return_value = [
            ("ou=Groups,dc=example,dc=com", {"cn": [b"group1"]})
        ]
        yield ldap_connection


@fixture
def auth_client(
    client, monkeypatch, tmp_path, gssapi_context, ldap_connection
):
    ldap_searches = [{"BASE": LDAP_BASE, "SEARCH_STRING": LDAP_SEARCH}]
    monkeypatch.setenv("PLM_LDAP_HOST", "ldap://ldap.example.com")
    monkeypatch.setenv("PLM_LDAP_SEARCHES", json.dumps(ldap_searches))

    permissions_file = tmp_path / "permissions.json"
    with open(permissions_file, "w") as f:
        json.dump(PERMISSIONS, f)
    monkeypatch.setenv("PLM_PERMISSIONS", str(permissions_file))

    load_config_from_env(client.application)
    yield client


def auth_headers():
    token = base64.b64encode(b"SECRET").decode("utf-8")
    return {"Authorization": f"Negotiate {token}"}
