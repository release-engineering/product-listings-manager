# SPDX-License-Identifier: MIT
import importlib.metadata as importlib_metadata

try:
    __version__ = importlib_metadata.version(__name__)
except importlib_metadata.PackageNotFoundError:
    # If the app is not installed but run from git repository clone, get the
    # version from pyproject.toml.
    import tomllib

    with open("pyproject.toml") as f:
        pyproject = tomllib.load(f)  # type: ignore

    __version__ = pyproject["tool"]["poetry"]["version"]
