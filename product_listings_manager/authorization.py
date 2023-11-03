# SPDX-License-Identifier: GPL-2.0+
import logging
from collections.abc import Generator
from dataclasses import dataclass

import ldap
from fastapi import HTTPException, status

log = logging.getLogger(__name__)


@dataclass
class LdapConfig:
    host: str
    searches: list[dict[str, str]]


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


def get_user_groups(user: str, ldap_config: LdapConfig) -> Generator[str, None, None]:
    try:
        ldap_connection = ldap.initialize(ldap_config.host)
        for ldap_search in ldap_config.searches:
            yield from get_group_membership(user, ldap_connection, ldap_search)
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
