def pytest_addoption(parser):
    parser.addoption('--live', action='store_true',
                     help='query live composedb and koji servers')
