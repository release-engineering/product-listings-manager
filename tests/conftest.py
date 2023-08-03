# Flask < 1.0 does not have get_json.
import os
import json
import pytest
from flask import Response

from product_listings_manager.app import create_app
from product_listings_manager.models import db


if not hasattr(Response, "get_json"):

    def get_json(self, force=False, silent=False, cache=True):
        """Minimal implementation we can use this in the tests."""
        return json.loads(self.data)

    Response.get_json = get_json


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
    skip_live = pytest.mark.skip(
        reason="use --live argument to query production servers"
    )
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)


@pytest.fixture
def app():
    os.environ["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
    app = create_app()
    with app.app_context():
        db.create_all()
        yield app


@pytest.fixture
def client(app):
    client = app.test_client()
    yield client
