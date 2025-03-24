# SPDX-License-Identifier: GPL-2.0+
from unittest.mock import ANY, Mock, patch

import koji
from pytest import fixture
from sqlalchemy.exc import SQLAlchemyError

from product_listings_manager import products
from product_listings_manager.models import get_db

from .factories import (
    ModulesFactory,
    OverridesFactory,
    PackagesFactory,
    ProductsFactory,
    TreesFactory,
)


@fixture
def exception_log(app):
    with patch(
        "product_listings_manager.utils.logger.exception", autospec=True
    ) as mocked:
        yield mocked


@fixture
def mock_koji_session():
    with patch("product_listings_manager.products.koji.ClientSession") as mocked:
        with patch("product_listings_manager.products.koji.read_config", autospec=True):
            yield mocked()


class TestIndex:
    def test_get_index(self, client):
        r = client.get("/api/v1.0/")
        expected_json = {
            "about_url": "http://testserver/api/v1.0/about",
            "health_url": "http://testserver/api/v1.0/health",
            "module_product_listings_url": "http://testserver/api/v1.0/module-product-listings/:label/:module_build_nvr",
            "product_info_url": "http://testserver/api/v1.0/product-info/:label",
            "product_listings_url": "http://testserver/api/v1.0/product-listings/:label/:build_info",
            "product_labels_url": "http://testserver/api/v1.0/product-labels",
            "permissions_url": "http://testserver/api/v1.0/permissions",
        }
        assert r.status_code == 200
        assert r.json() == expected_json


class TestAbout:
    def test_get_version(self, client):
        from product_listings_manager import __version__

        r = client.get("/api/v1.0/about")
        assert r.status_code == 200
        assert r.json() == {
            "source": "https://github.com/release-engineering/product-listings-manager",
            "version": __version__,
        }


class TestHealth:
    def test_health_db_fail(self, client, app):
        async def mock_get_db():
            mocked = Mock()
            mocked().execute.side_effect = SQLAlchemyError("db connect error")
            return mocked()

        app.dependency_overrides[get_db] = mock_get_db
        r = client.get("/api/v1.0/health")
        assert r.status_code == 503, r.text
        assert "DB Error:" in r.json().get("message", "")

    def test_health_permissions_file_not_found(self, client, monkeypatch, tmp_path):
        permissions_file = tmp_path / "permissions_empty.json"
        monkeypatch.setenv("PLM_PERMISSIONS", str(permissions_file))

        r = client.get("/api/v1.0/health")
        assert r.status_code == 503, r.text
        assert "Failed to parse permissions configuration:" in r.json().get(
            "message", ""
        )

    def test_health_permissions_file_invalid(self, client, monkeypatch, tmp_path):
        permissions_file = tmp_path / "permissions_bad.json"
        with open(permissions_file, "w") as f:
            f.write("[{}]")

        monkeypatch.setenv("PLM_PERMISSIONS", str(permissions_file))

        r = client.get("/api/v1.0/health")
        assert r.status_code == 503, r.text
        assert "Failed to parse permissions configuration:" in r.json().get(
            "message", ""
        )

    @patch("product_listings_manager.rest_api_v1.products.get_koji_session")
    def test_health_koji_fail(self, mock_koji, client):
        mock_koji.side_effect = Exception("koji connect error")
        r = client.get("/api/v1.0/health")
        assert r.status_code == 503, r.text
        assert "Koji Error: koji connect error" in r.json().get("message")

    @patch("product_listings_manager.rest_api_v1.products.get_koji_session")
    def test_health_ok(self, mock_koji, client):
        mock_koji.return_value.getAPIVersion.return_value = 1
        r = client.get("/api/v1.0/health")
        assert r.status_code == 200, r.text
        assert r.json() == {"message": "It works!"}


class TestProductInfo:
    product_label = "Fake-product"
    path = f"/api/v1.0/product-info/{product_label}"

    def test_get_product_info(self, client):
        product_version = "7.3"
        p1 = ProductsFactory(
            label=self.product_label, version=product_version, variant="Client"
        )
        p2 = ProductsFactory(
            label=self.product_label, version=product_version, variant="Server"
        )
        r = client.get(self.path)
        assert r.status_code == 200
        assert r.json() == [product_version, [p1.variant, p2.variant]]

    def test_label_not_found(self, client):
        msg = f"Could not find a product with label: {self.product_label}"
        r = client.get(self.path)
        assert r.status_code == 404
        assert msg in r.json().get("message", "")

    @patch("product_listings_manager.products.get_product_info")
    def test_unknown_error(self, mock_getinfo, exception_log, client):
        mock_getinfo.side_effect = Exception("Unexpected error")
        r = client.get(self.path)
        assert r.status_code == 500
        exception_log.assert_any_call(
            "%s: callee=%r, args=%r, kwargs=%r",
            "API call get_product_info() failed",
            ANY,
            (self.product_label,),
            {},
        )


class TestProductListings:
    product_label = "RHEL-6-Server-EXTRAS-6"
    pkg_name = "dumb-init"
    pkg_version = "1.2.0"
    pkg_release = "1.20170802gitd283f8a.el6"
    nvr = f"{pkg_name}-{pkg_version}-{pkg_release}"
    path = f"/api/v1.0/product-listings/{product_label}/{nvr}"

    def test_get_product_listings(self, mock_koji_session, client):
        mock_koji_session.getBuild.return_value = {
            "id": 1,
            "package_name": self.pkg_name,
            "version": self.pkg_version,
            "release": self.pkg_release,
        }

        # mock result of koji listRPMs() API
        debuginfo_pkg_name = f"{self.pkg_name}-debuginfo"
        debuginfo_nvr = f"{debuginfo_pkg_name}-{self.pkg_version}-{self.pkg_release}"
        mock_koji_session.listRPMs.return_value = [
            {
                "arch": "s390x",
                "name": debuginfo_pkg_name,
                "nvr": debuginfo_nvr,
            },
            {"arch": "s390x", "name": self.pkg_name, "nvr": self.nvr},
            {
                "arch": "x86_64",
                "name": debuginfo_pkg_name,
                "nvr": debuginfo_nvr,
            },
            {"arch": "x86_64", "name": self.pkg_name, "nvr": self.nvr},
            {"arch": "src", "name": self.pkg_name, "nvr": self.nvr},
        ]

        # Create products, trees, packages records in db
        variant = "EXTRAS-6"
        p = ProductsFactory(label=self.product_label, variant=variant)
        t = TreesFactory(arch="x86_64")
        t.products.append(p)
        pkg = PackagesFactory(
            name=self.pkg_name, version=self.pkg_version, arch="x86_64"
        )
        pkg_src = PackagesFactory(
            name=self.pkg_name, version=self.pkg_version, arch="src"
        )
        t.packages.append(pkg)
        t.packages.append(pkg_src)
        TreesFactory._meta.sqlalchemy_session.commit()

        r = client.get(self.path)
        assert r.status_code == 200, r.text
        assert r.json() == {
            variant: {
                self.nvr: {"x86_64": ["x86_64"], "src": ["x86_64"]},
                debuginfo_nvr: {"x86_64": ["x86_64"]},
            }
        }

    @patch("product_listings_manager.products.get_product_listings")
    def test_product_listings_not_found(self, mock_get_product_listings, client):
        error_message = "NOT FOUND"
        mock_get_product_listings.side_effect = products.ProductListingsNotFoundError(
            error_message
        )
        r = client.get(self.path)
        assert r.status_code == 404
        assert r.json() == {"message": error_message}

    @patch("product_listings_manager.products.get_product_listings")
    def test_unknown_error(self, mock_getlistings, exception_log, client):
        mock_getlistings.side_effect = Exception("Unexpected error")
        r = client.get(self.path)
        assert r.status_code == 500
        exception_log.assert_any_call(
            "%s: callee=%r, args=%r, kwargs=%r",
            "API call get_product_listings() failed",
            ANY,
            (self.product_label, self.nvr),
            {},
        )

    def test_get_product_listings_src_only(self, mock_koji_session, client):
        mock_koji_session.getBuild.return_value = {
            "id": 1,
            "package_name": self.pkg_name,
            "version": self.pkg_version,
            "release": self.pkg_release,
        }

        # mock result of koji listRPMs() API
        mock_koji_session.listRPMs.return_value = [
            {"arch": "src", "name": self.pkg_name, "nvr": self.nvr}
        ]

        # Create products, trees, packages records in db
        variant = "EXTRAS-6"
        p = ProductsFactory(
            label=self.product_label, variant=variant, allow_source_only=False
        )
        t = TreesFactory(arch="x86_64")
        t.products.append(p)
        pkg_src = PackagesFactory(
            name=self.pkg_name, version=self.pkg_version, arch="src"
        )
        t.packages.append(pkg_src)
        TreesFactory._meta.sqlalchemy_session.commit()

        # Should return empty product listings because only src package found
        # but allow_source_only=False
        r = client.get(self.path)
        assert r.status_code == 200
        assert r.json() == {}

        # Set allow_source_only to True and then it should return non-empty listings
        p.allow_source_only = True
        TreesFactory._meta.sqlalchemy_session.commit()
        r = client.get(self.path)
        assert r.status_code == 200
        assert r.json() == {variant: {self.nvr: {"src": ["x86_64"]}}}

    def test_get_product_listings_missing_build(self, mock_koji_session, client):
        error = f"No such build: '{self.nvr}'"
        mock_koji_session.getBuild.side_effect = koji.GenericError(error)
        r = client.get(self.path)
        assert r.status_code == 404
        assert r.json() == {"message": error}

    def test_get_product_listing_overrides(self, mock_koji_session, client):
        self.pkg_name = "dumb-1.2-fastdebug-debuginfo"
        mock_koji_session.getBuild.return_value = {
            "id": 1,
            "package_name": self.pkg_name,
            "version": self.pkg_version,
            "release": self.pkg_release,
        }

        mock_koji_session.listRPMs.return_value = [
            {"arch": "x86_64", "name": self.pkg_name, "nvr": self.nvr},
            {"arch": "src", "name": self.pkg_name, "nvr": self.nvr},
        ]

        variant = "EXTRAS-6"
        p = ProductsFactory(label=self.product_label, variant=variant)
        for arch in ("x86_64", "src"):
            t = TreesFactory(arch=arch)
            t.products.append(p)
            pkg = PackagesFactory(
                name=self.pkg_name, version=self.pkg_version, arch=arch
            )
            t.packages.append(pkg)
        TreesFactory._meta.sqlalchemy_session.commit()

        r = client.get(self.path)
        assert r.status_code == 200, r.text
        assert r.json() == {
            variant: {
                self.nvr: {"x86_64": ["x86_64"], "src": ["src"]},
            }
        }

        o = OverridesFactory(
            name=self.pkg_name,
            pkg_arch="src",
            product_arch="src",
            product=p.id,
            include=False,
        )
        p.overrides.append(o)
        ProductsFactory._meta.sqlalchemy_session.commit()

        r = client.get(self.path)
        assert r.status_code == 200, r.text
        assert r.json() == {
            variant: {
                self.nvr: {"x86_64": ["x86_64"]},
            }
        }

        o.include = True
        o.pkg_arch = "src"
        o.product_arch = "x86_64"
        OverridesFactory._meta.sqlalchemy_session.commit()

        r = client.get(self.path)
        assert r.status_code == 200, r.text
        assert r.json() == {
            variant: {
                self.nvr: {"x86_64": ["x86_64"], "src": ["src", "x86_64"]},
            }
        }


class TestModuleProductListings:
    product_label = "RHEL-8.0.0"
    module_name = "ruby"
    module_stream = "2.5"
    nvr = f"{module_name}-{module_stream}-820181217154935.9edba152"
    path = f"/api/v1.0/module-product-listings/{product_label}/{nvr}"

    def test_get_module_product_listings(self, mock_koji_session, client):
        mock_koji_session.getBuild.return_value = {
            "extra": {
                "typeinfo": {
                    "module": {
                        "name": self.module_name,
                        "stream": self.module_stream,
                    }
                }
            }
        }
        variant = "AppStream-8.0.0"
        p = ProductsFactory(label=self.product_label, version="8.0.0", variant=variant)
        m = ModulesFactory(name=self.module_name, stream=self.module_stream)
        t = TreesFactory()
        t.products.append(p)
        t.modules.append(m)
        TreesFactory._meta.sqlalchemy_session.commit()

        r = client.get(self.path)
        assert r.status_code == 200
        assert r.json() == {variant: [t.arch]}

    @patch("product_listings_manager.products.get_module_product_listings")
    def test_product_listings_not_found(self, mock_get_module_product_listings, client):
        error_message = "NOT FOUND"
        mock_get_module_product_listings.side_effect = (
            products.ProductListingsNotFoundError(error_message)
        )
        r = client.get(self.path)
        assert r.status_code == 404
        assert error_message in r.json().get("message", "")

    @patch("product_listings_manager.products.get_module_product_listings")
    def test_unknown_error(self, mock_getlistings, exception_log, client):
        mock_getlistings.side_effect = Exception("Unexpected error")
        r = client.get(self.path)
        assert r.status_code == 500
        exception_log.assert_any_call(
            "%s: callee=%r, args=%r, kwargs=%r",
            "API call get_module_product_listings() failed",
            ANY,
            (self.product_label, self.nvr),
            {},
        )


class TestLabels:
    @patch("product_listings_manager.products.get_product_labels")
    def test_unknown_error(self, mock_getlabels, exception_log, client):
        mock_getlabels.side_effect = Exception("Unexpected error")
        r = client.get("/api/v1.0/product-labels")
        assert r.status_code == 500
        exception_log.assert_any_call(
            "%s: callee=%r, args=%r, kwargs=%r",
            "API call get_product_labels() failed",
            ANY,
            (),
            {},
        )

    def test_get_product_lables(self, client):
        p1 = ProductsFactory()
        p2 = ProductsFactory()
        r = client.get("/api/v1.0/product-labels")
        assert r.status_code == 200
        assert r.json() == [{"label": p1.label}, {"label": p2.label}]
