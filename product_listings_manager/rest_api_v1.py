# SPDX-License-Identifier: GPL-2.0+
from typing import Any

from flask import Blueprint, current_app, request, url_for
from flask_restful import Api, Resource
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import InternalServerError, NotFound, Unauthorized

from product_listings_manager import __version__, products, utils
from product_listings_manager.auth import get_user
from product_listings_manager.authorization import LdapConfig, get_user_groups
from product_listings_manager.db_queries import (
    execute_queries,
    queries_from_user_input,
    validate_queries,
)
from product_listings_manager.models import db
from product_listings_manager.permissions import has_permission

blueprint = Blueprint("api_v1", __name__)


def ldap_config() -> LdapConfig:
    ldap_host = current_app.config.get("LDAP_HOST")
    ldap_searches = current_app.config.get("LDAP_SEARCHES")

    if not ldap_host or not ldap_searches:
        raise InternalServerError(
            "Server configuration LDAP_HOST and LDAP_SEARCHES is required."
        )

    return LdapConfig(host=ldap_host, searches=ldap_searches)


def permissions() -> list[dict[str, Any]]:
    """
    Return PERMISSIONS configuration.
    """
    return current_app.config.get("PERMISSIONS", [])


class Index(Resource):
    def get(self):
        """Link to the the v1 API endpoints."""
        return {
            "about_url": url_for(".about", _external=True),
            "health_url": url_for(".health", _external=True),
            "product_info_url": url_for(
                ".productinfo", label=":label", _external=True
            ),
            "product_labels_url": url_for(".productlabels", _external=True),
            "product_listings_url": url_for(
                ".productlistings",
                label=":label",
                build_info=":build_info",
                _external=True,
            ),
            "module_product_listings_url": url_for(
                ".moduleproductlistings",
                label=":label",
                module_build_nvr=":module_build_nvr",
                _external=True,
            ),
        }


class About(Resource):
    def get(self):
        return {
            "source": "https://github.com/release-engineering/product-listings-manager",
            "version": __version__,
        }


class Health(Resource):
    def get(self):
        """Provides status report

        * 200 if everything is ok
        * 503 if service is not working as expected
        """

        try:
            db.session.execute(db.text("SELECT 1"))
        except SQLAlchemyError as e:
            current_app.logger.warning("DB health check failed: %s", e)
            return {"ok": False, "message": f"DB Error: {e}"}, 503

        try:
            products.get_koji_session().getAPIVersion()
        except Exception as e:
            current_app.logger.warning("Koji health check failed: %s", e)
            return {"ok": False, "message": f"Koji Error: {e}"}, 503

        return {"ok": True, "message": "It works!"}


class Login(Resource):
    def get(self):
        ldap_config_ = ldap_config()
        user, headers = get_user(request)
        groups = set(get_user_groups(user, ldap_config_))

        return {
            "user": user,
            "groups": sorted(groups),
        }


class ProductInfo(Resource):
    def get(self, label):
        try:
            versions, variants = products.getProductInfo(label)
        except products.ProductListingsNotFoundError as ex:
            raise NotFound(str(ex))
        except Exception:
            utils.log_remote_call_error(
                "API call getProductInfo() failed", label
            )
            raise
        return [versions, variants]


class ProductLabels(Resource):
    def get(self):
        try:
            return products.getProductLabels()
        except Exception:
            utils.log_remote_call_error("API call getProductLabels() failed")
            raise


class ProductListings(Resource):
    def get(self, label, build_info):
        try:
            return products.getProductListings(label, build_info)
        except products.ProductListingsNotFoundError as ex:
            raise NotFound(str(ex))
        except Exception:
            utils.log_remote_call_error(
                "API call getProductListings() failed", label, build_info
            )
            raise


class ModuleProductListings(Resource):
    def get(self, label, module_build_nvr):
        try:
            return products.getModuleProductListings(label, module_build_nvr)
        except products.ProductListingsNotFoundError as ex:
            raise NotFound(str(ex))
        except Exception:
            utils.log_remote_call_error(
                "API call getModuleProductListings() failed",
                label,
                module_build_nvr,
            )
            raise


class Permissions(Resource):
    def get(self):
        return permissions()


class DBQuery(Resource):
    def post(self):
        ldap_config_ = ldap_config()
        user, headers = get_user(request)
        input = request.get_json(force=True)
        queries = queries_from_user_input(input)
        validate_queries(queries)

        if not has_permission(user, queries, permissions(), ldap_config_):
            current_app.logger.warning("Unauthorized access for user %s", user)
            raise Unauthorized(
                f"User {user} is not authorized to use this query"
            )

        current_app.logger.info(
            "Authorized access for user %s; input: %s", user, input
        )

        return execute_queries(queries), 200


api = Api(blueprint)
api.add_resource(Index, "/")
api.add_resource(About, "/about")
api.add_resource(Health, "/health")
api.add_resource(Login, "/login")
api.add_resource(ProductInfo, "/product-info/<label>")
api.add_resource(ProductLabels, "/product-labels")
api.add_resource(ProductListings, "/product-listings/<label>/<build_info>")
api.add_resource(
    ModuleProductListings,
    "/module-product-listings/<label>/<module_build_nvr>",
)
api.add_resource(Permissions, "/permissions")
api.add_resource(DBQuery, "/dbquery")
