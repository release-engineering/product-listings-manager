from __future__ import annotations

import os
import threading
from dataclasses import dataclass

import koji
from cachetools import TTLCache, cached

from product_listings_manager.exceptions import ProductListingsNotFoundError

KOJI_CONFIG_PROFILE = os.getenv("PLM_KOJI_CONFIG_PROFILE", "brew")
KOJI_CACHE_TTL = float(os.getenv("PLM_KOJI_CACHE_TTL", "3600"))
KOJI_CACHE_MAX_SIZE = int(os.getenv("PLM_KOJI_CACHE_MAX_SIZE", "1024"))


@dataclass(frozen=True, slots=True)
class KojiBuild:
    id: int
    package_name: str
    version: str
    release: str
    module_name: str
    module_stream: str


@dataclass(frozen=True, slots=True)
class KojiRpm:
    name: str
    arch: str
    nvr: str
    version: str


_build_cache: TTLCache = TTLCache(maxsize=KOJI_CACHE_MAX_SIZE, ttl=KOJI_CACHE_TTL)
_build_cache_lock = threading.Lock()

_rpms_cache: TTLCache = TTLCache(maxsize=KOJI_CACHE_MAX_SIZE, ttl=KOJI_CACHE_TTL)
_rpms_cache_lock = threading.Lock()


def get_koji_session():
    """
    Get a new koji session for accessing kojihub functions.
    """
    conf = koji.read_config(KOJI_CONFIG_PROFILE)
    hub = conf["server"]
    return koji.ClientSession(hub, {})


@cached(
    cache=_build_cache,
    lock=_build_cache_lock,
    key=lambda nvr, session: nvr,
)
def get_build(nvr, session):
    """
    Get a build from kojihub.
    """
    try:
        build = session.getBuild(nvr, strict=True)
    except koji.GenericError as ex:
        raise ProductListingsNotFoundError(str(ex))
    module = {}
    try:
        module = build["extra"]["typeinfo"]["module"]
    except (KeyError, TypeError):
        pass
    return KojiBuild(
        id=build["id"],
        package_name=build["package_name"],
        version=build["version"],
        release=build["release"],
        module_name=module.get("name", ""),
        module_stream=module.get("stream", ""),
    )


@cached(
    cache=_rpms_cache,
    lock=_rpms_cache_lock,
    key=lambda build_id, session: build_id,
)
def get_rpms(build_id, session):
    return [
        KojiRpm(
            name=rpm["name"],
            arch=rpm["arch"],
            nvr=rpm["nvr"],
            version=rpm["version"],
        )
        for rpm in session.listRPMs(buildID=build_id)
    ]
