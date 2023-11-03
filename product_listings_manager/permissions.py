# SPDX-License-Identifier: GPL-2.0+
import re
from fnmatch import fnmatchcase

from product_listings_manager.authorization import LdapConfig, get_user_groups
from product_listings_manager.schemas import Permission, SqlQuery


def normalize(text):
    return re.sub(r"\s+", " ", text.strip().upper())


def query_matches(query: str, permission: Permission) -> bool:
    return any(
        fnmatchcase(normalize(query), normalize(pattern))
        for pattern in permission.queries
    )


def has_permission(
    user: str,
    queries: list[SqlQuery],
    permissions: list[Permission],
    ldap_config: LdapConfig,
) -> bool:
    qs = list(q.query for q in queries)
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

    groups = set(get_user_groups(user, ldap_config))
    qs = [
        q
        for q in qs
        if not any(
            not groups.isdisjoint(p.groups) and query_matches(q, p) for p in permissions
        )
    ]
    return not qs
