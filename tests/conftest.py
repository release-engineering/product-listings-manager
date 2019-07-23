# Flask < 1.0 does not have get_json.
from flask import Response
import json
import pytest

from product_listings_manager.app import create_app


if not hasattr(Response, 'get_json'):
    def get_json(self, force=False, silent=False, cache=True):
        """ Minimal implementation we can use this in the tests. """
        return json.loads(self.data)
    Response.get_json = get_json


def pytest_addoption(parser):
    parser.addoption('--live', action='store_true', default=False,
                     help='query live composedb and koji servers')


def pytest_configure(config):
    config.addinivalue_line("markers", "live: mark test as requiring live composedb and koji servers")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--live"):
        return
    skip_live = pytest.mark.skip(reason="use --live argument to query production servers")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)


@pytest.fixture
def client():
    client = create_app().test_client()
    yield client
