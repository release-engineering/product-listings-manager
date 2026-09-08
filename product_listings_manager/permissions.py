# SPDX-License-Identifier: GPL-2.0+
import json
import os
import re
from fnmatch import fnmatchcase

from product_listings_manager.authorization import LdapConfig, get_user_groups
from product_listings_manager.schemas import Permission, SqlQuery


def normalize(text):
    return re.sub(r"\s+", " ", text.upper()).strip(" ;")


def query_matches(query: str, permission: Permission) -> bool:
    return any(
        fnmatchcase(normalize(query), normalize(pattern))
        for pattern in permission.queries
    )


async def load_permissions() -> list[Permission]:
    """
    Load permissions configuration from file.

    Called once at app startup event handler.
    If this fails, the application will not start.

    Uses asyncio.to_thread() to avoid blocking the event loop during I/O.
    """
    import asyncio

    def _load() -> list[Permission]:
        filename = os.getenv("PLM_PERMISSIONS")
        if not filename:
            return []

        with open(filename) as f:
            return [Permission.model_validate(x) for x in json.load(f)]

    return await asyncio.to_thread(_load)


def has_permission(
    user: str,
    queries: list[SqlQuery],
    permissions: list[Permission],
    ldap_config: LdapConfig,
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

    groups = set(get_user_groups(user, ldap_config))
    qs = [
        q
        for q in qs
        if not any(
            not groups.isdisjoint(p.groups) and query_matches(q, p) for p in permissions
        )
    ]
    return not qs
