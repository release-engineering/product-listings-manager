# SPDX-License-Identifier: GPL-2.0+
import logging
import re
from fnmatch import fnmatchcase

from product_listings_manager.authorization import LdapConfig, get_user_groups
from product_listings_manager.schemas import Permission, SqlQuery

log = logging.getLogger(__name__)


def normalize(text):
    return re.sub(r"\s+", " ", text.upper()).strip(" ;")


def query_matches(query: str, permission: Permission) -> bool:
    return any(
        fnmatchcase(normalize(query), normalize(pattern))
        for pattern in permission.queries
    )


def groups_authorize_queries(
    queries: list[str], groups: set[str], permissions: list[Permission]
) -> bool:
    """Check if the given groups authorize all queries."""
    return all(
        any(
            not groups.isdisjoint(p.groups) and query_matches(q, p) for p in permissions
        )
        for q in queries
    )


def has_permission(
    user: str,
    queries: list[SqlQuery],
    permissions: list[Permission],
    ldap_config: LdapConfig,
    oidc_groups: list[str] | None = None,
) -> bool:
    qs = [q.query for q in queries]
    qs = [
        q
        for q in qs
        if not any(user in p.users and query_matches(q, p) for p in permissions)
    ]
    if not qs:
        return True

    # Avoid querying LDAP unnecessarily
    if not any(p.groups for p in permissions):
        return False

    # OIDC groups check (no network calls needed)
    if oidc_groups is not None:
        if not oidc_groups:
            log.warning(
                "OIDC token for user %s contains an empty groups claim; "
                "falling back to LDAP",
                user,
            )
        elif groups_authorize_queries(qs, set(oidc_groups), permissions):
            return True
        else:
            log.warning(
                "OIDC groups %r did not fully authorize user %s; falling back to LDAP",
                oidc_groups,
                user,
            )

    ldap_groups = get_user_groups(user, ldap_config)
    if groups_authorize_queries(qs, set(ldap_groups), permissions):
        if oidc_groups is not None:
            log.warning(
                "LDAP authorized user %s. "
                "Consider adding the appropriate groups to the user's "
                "OIDC token to avoid LDAP dependency.",
                user,
            )
        return True

    return False
