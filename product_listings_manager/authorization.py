# SPDX-License-Identifier: GPL-2.0+
import logging
import os
from collections.abc import Generator
from dataclasses import dataclass

import gssapi
import gssapi.raw
import ldap
from fastapi import HTTPException, status

log = logging.getLogger(__name__)


def _init_gssapi_credentials():
    """Acquire GSSAPI initiator credentials from the keytab."""
    keytab = os.environ.get("KRB5_KTNAME")
    if not keytab:
        raise RuntimeError("KRB5_KTNAME environment variable is not set")

    creds = gssapi.Credentials(usage="initiate", store={"client_keytab": keytab})
    gssapi.raw.store_cred(creds, usage="initiate", overwrite=True, set_default=True)


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


def get_user_groups(user: str, ldap_config: LdapConfig) -> Generator[str, None, None]:
    try:
        ldap_connection = ldap.initialize(ldap_config.host)
        if ldap_config.use_gssapi:
            _init_gssapi_credentials()
            ldap_connection.sasl_interactive_bind_s("", ldap.sasl.gssapi())
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
