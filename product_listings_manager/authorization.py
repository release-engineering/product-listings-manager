# SPDX-License-Identifier: GPL-2.0+
import logging
import os
import threading
from collections.abc import Generator
from dataclasses import dataclass

import ldap
import ldap.ldapobject
from cachetools import TTLCache, cached
from fastapi import HTTPException, status

log = logging.getLogger(__name__)

LDAP_RETRY_COUNT = int(os.getenv("PLM_LDAP_RETRY_COUNT", "5"))
LDAP_RETRY_DELAY_SECONDS = float(os.getenv("PLM_LDAP_RETRY_DELAY", "15"))
LDAP_CACHE_TTL_SECONDS = float(os.getenv("PLM_LDAP_CACHE_TTL", "300"))
LDAP_CACHE_MAX_SIZE = int(os.getenv("PLM_LDAP_CACHE_MAX_SIZE", "256"))

_group_cache: TTLCache = TTLCache(
    maxsize=LDAP_CACHE_MAX_SIZE, ttl=LDAP_CACHE_TTL_SECONDS
)
_group_cache_lock = threading.Lock()


@dataclass
class LdapConfig:
    host: str
    searches: list[dict[str, str]]
    use_gssapi: bool = False


def get_group_membership(
    user: str, ldap_connection, ldap_search: dict[str, str]
) -> list[str]:
    results = ldap_connection.search_s(
        ldap_search["BASE"],
        ldap.SCOPE_SUBTREE,
        ldap_search["SEARCH_STRING"].format(user=user),
        ["cn"],
    )
    return [group[1]["cn"][0].decode("utf-8") for group in results]


@cached(cache=_group_cache, key=lambda user, _: user, lock=_group_cache_lock)
def _fetch_user_groups(user: str, ldap_config: LdapConfig) -> list[str]:
    ldap_connection = ldap.ldapobject.ReconnectLDAPObject(
        ldap_config.host,
        retry_max=LDAP_RETRY_COUNT,
        retry_delay=LDAP_RETRY_DELAY_SECONDS,
    )
    try:
        if ldap_config.use_gssapi:
            ldap_connection.sasl_gssapi_bind_s()
        groups = []
        for ldap_search in ldap_config.searches:
            groups.extend(get_group_membership(user, ldap_connection, ldap_search))
        return groups
    finally:
        ldap_connection.unbind_s()


def get_user_groups(user: str, ldap_config: LdapConfig) -> Generator[str, None, None]:
    try:
        groups = _fetch_user_groups(user, ldap_config)
    except ldap.SERVER_DOWN:
        log.exception("The LDAP server is unreachable")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The LDAP server is unreachable",
        )
    except ldap.LDAPError:
        log.exception("Unexpected LDAP connection error")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unexpected LDAP connection error",
        )

    yield from groups
