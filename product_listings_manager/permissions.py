# SPDX-License-Identifier: GPL-2.0+
from fnmatch import fnmatchcase
from typing import Any

from product_listings_manager.authorization import LdapConfig, get_user_groups


def query_matches(query: str, permission: dict[str, Any]) -> bool:
    return any(
        fnmatchcase(query.upper(), pattern.upper())
        for pattern in permission.get("queries", [])
    )


def has_permission(
    user: str,
    queries: list[dict[str, str]],
    permissions: list[dict[str, Any]],
    ldap_config: LdapConfig,
) -> bool:
    qs = list(q["query"] for q in queries)
    qs = [
        q
        for q in qs
        if not any(
            user in p.get("users", set()) and query_matches(q, p)
            for p in permissions
        )
    ]
    if not qs:
        return True

    # Avoid querying LDAP unnecessarily
    if not any(p.get("groups") for p in permissions):
        return False

    groups = set(get_user_groups(user, ldap_config))
    qs = [
        q
        for q in qs
        if not any(
            not groups.isdisjoint(p.get("groups", set()))
            and query_matches(q, p)
            for p in permissions
        )
    ]
    return not qs
