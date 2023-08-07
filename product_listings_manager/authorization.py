# SPDX-License-Identifier: GPL-2.0+
import logging

import ldap
from werkzeug.exceptions import BadGateway

log = logging.getLogger(__name__)


def get_group_membership(user, ldap_connection, ldap_search):
    results = ldap_connection.search_s(
        ldap_search["BASE"],
        ldap.SCOPE_SUBTREE,
        ldap_search["SEARCH_STRING"].format(user=user),
        ["cn"],
    )
    return [group[1]["cn"][0].decode("utf-8") for group in results]


def get_user_groups(user, ldap_host, ldap_searches):
    try:
        ldap_connection = ldap.initialize(ldap_host)
        for cur_ldap_search in ldap_searches:
            yield from get_group_membership(
                user, ldap_connection, cur_ldap_search
            )
    except ldap.SERVER_DOWN:
        log.exception("The LDAP server is unreachable")
        raise BadGateway("The LDAP server is unreachable")
    except ldap.LDAPError:
        log.exception("Unexpected LDAP connection error")
        raise BadGateway("Unexpected LDAP connection error")
