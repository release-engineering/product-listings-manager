# Flask < 1.0 does not have get_json.
from flask import Response
import json
if not hasattr(Response, 'get_json'):
    def get_json(self, force=False, silent=False, cache=True):
        """ Minimal implementation we can use this in the tests. """
        return json.loads(self.data)
    Response.get_json = get_json


def pytest_addoption(parser):
    parser.addoption('--live', action='store_true',
                     help='query live composedb and koji servers')
