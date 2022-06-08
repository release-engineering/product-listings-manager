from mock import patch

from sqlalchemy.exc import SQLAlchemyError

from product_listings_manager import products

from .factories import PackagesFactory
from .factories import ProductsFactory
from .factories import ModulesFactory
from .factories import TreesFactory


class TestIndex(object):
    def test_get_index(self, client):
        r = client.get("/api/v1.0/")
        expected_json = {
            "about_url": "http://localhost/api/v1.0/about",
            "health_url": "http://localhost/api/v1.0/health",
            "module_product_listings_url": "http://localhost/api/v1.0/module-product-listings/:label/:module_build_nvr",
            "product_info_url": "http://localhost/api/v1.0/product-info/:label",
            "product_listings_url": "http://localhost/api/v1.0/product-listings/:label/:build_info",
            "product_labels_url": "http://localhost/api/v1.0/product-labels",
        }
        assert r.status_code == 200
        assert r.get_json() == expected_json


class TestAbout(object):
    def test_get_version(self, client):
        from product_listings_manager import __version__

        r = client.get("/api/v1.0/about")
        assert r.status_code == 200
        assert r.get_json() == {
            "source": "https://github.com/release-engineering/product-listings-manager",
            "version": __version__,
        }


class TestHealth(object):
    @patch("product_listings_manager.rest_api_v1.db.engine.execute")
    def test_health_db_fail(self, mock_db, client):
        mock_db.side_effect = SQLAlchemyError("db connect error")
        r = client.get("/api/v1.0/health")
        assert r.status_code == 503
        data = r.get_json()
        assert data["ok"] is False
        assert "DB Error:" in data["message"]

    @patch("product_listings_manager.rest_api_v1.products.get_koji_session")
    def test_health_koji_fail(self, mock_koji, client):
        mock_koji.side_effect = Exception("koji connect error")
        r = client.get("/api/v1.0/health")
        assert r.status_code == 503
        data = r.get_json()
        assert data["ok"] is False
        assert "Koji Error: koji connect error" in data["message"]

    @patch("product_listings_manager.rest_api_v1.products.get_koji_session")
    def test_health_ok(self, mock_koji, client):
        mock_koji.return_value.getAPIVersion.return_value = 1
        r = client.get("/api/v1.0/health")
        assert r.status_code == 200
        assert r.get_json() == {"ok": True, "message": "It works!"}


class TestProductInfo(object):
    product_label = "Fake-product"
    path = "/api/v1.0/product-info/{0}".format(product_label)

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
        assert r.get_json() == [product_version, [p1.variant, p2.variant]]

    def test_label_not_found(self, client):
        msg = "Could not find a product with label: %s" % self.product_label
        r = client.get(self.path)
        assert r.status_code == 404
        assert msg in r.get_json()["message"]

    @patch("product_listings_manager.products.getProductInfo")
    @patch("product_listings_manager.utils.log_remote_call_error")
    def test_unknown_error(self, mock_log, mock_getinfo, client):
        mock_getinfo.side_effect = Exception("Unexpected error")
        r = client.get(self.path)
        assert r.status_code == 500
        mock_log.assert_called_once_with(
            "API call getProductInfo() failed", self.product_label
        )


class TestProductListings(object):
    product_label = "RHEL-6-Server-EXTRAS-6"
    pkg_name = "dumb-init"
    pkg_version = "1.2.0"
    pkg_release = "1.20170802gitd283f8a.el6"
    nvr = "{}-{}-{}".format(pkg_name, pkg_version, pkg_release)
    path = "/api/v1.0/product-listings/{0}/{1}".format(product_label, nvr)

    @patch("product_listings_manager.products.get_build")
    @patch("product_listings_manager.products.get_koji_session")
    def test_get_product_listings(self, mock_koji_session, mock_get_build, client):
        mock_get_build.return_value = {
            "id": 1,
            "package_name": self.pkg_name,
            "version": self.pkg_version,
            "release": self.pkg_release,
        }

        # mock result of koji listRPMs() API
        debuginfo_pkg_name = "{}-debuginfo".format(self.pkg_name)
        debuginfo_nvr = "{}-{}-{}".format(
            debuginfo_pkg_name, self.pkg_version, self.pkg_release
        )
        mock_koji_session.return_value.listRPMs.return_value = [
            {"arch": "s390x", "name": debuginfo_pkg_name, "nvr": debuginfo_nvr},
            {"arch": "s390x", "name": self.pkg_name, "nvr": self.nvr},
            {"arch": "x86_64", "name": debuginfo_pkg_name, "nvr": debuginfo_nvr},
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

        r = client.get(self.path)
        assert r.status_code == 200
        assert r.get_json() == {
            variant: {
                self.nvr: {"x86_64": ["x86_64"], "src": ["x86_64"]},
                debuginfo_nvr: {"x86_64": ["x86_64"]},
            }
        }

    @patch("product_listings_manager.products.getProductListings")
    def test_product_listings_not_found(self, mock_get_product_listings, client):
        error_message = "NOT FOUND"
        mock_get_product_listings.side_effect = products.ProductListingsNotFoundError(
            error_message
        )
        r = client.get(self.path)
        assert r.status_code == 404
        assert r.get_json() == {"message": error_message}

    @patch("product_listings_manager.products.getProductListings")
    @patch("product_listings_manager.utils.log_remote_call_error")
    def test_unknown_error(self, mock_log, mock_getlistings, client):
        mock_getlistings.side_effect = Exception("Unexpected error")
        r = client.get(self.path)
        assert r.status_code == 500
        mock_log.assert_called_once_with(
            "API call getProductListings() failed", self.product_label, self.nvr
        )

    @patch("product_listings_manager.products.get_build")
    @patch("product_listings_manager.products.get_koji_session")
    def test_get_product_listings_src_only(
        self, mock_koji_session, mock_get_build, client
    ):
        mock_get_build.return_value = {
            "id": 1,
            "package_name": self.pkg_name,
            "version": self.pkg_version,
            "release": self.pkg_release,
        }

        # mock result of koji listRPMs() API
        mock_koji_session.return_value.listRPMs.return_value = [
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

        # Should return empty product listings because only src package found but allow_source_only=False
        r = client.get(self.path)
        assert r.status_code == 200
        assert r.get_json() == {}

        # Set allow_source_only to True and then it should return non-empty listings
        p.allow_source_only = True
        r = client.get(self.path)
        assert r.status_code == 200
        assert r.get_json() == {variant: {self.nvr: {"src": ["x86_64"]}}}


class TestModuleProductListings(object):
    product_label = "RHEL-8.0.0"
    module_name = "ruby"
    module_stream = "2.5"
    nvr = "{}-{}-820181217154935.9edba152".format(module_name, module_stream)
    path = "/api/v1.0/module-product-listings/{0}/{1}".format(product_label, nvr)

    @patch("product_listings_manager.products.get_build")
    def test_get_module_product_listings(self, mock_get_build, client):
        mock_get_build.return_value = {
            "extra": {
                "typeinfo": {
                    "module": {"name": self.module_name, "stream": self.module_stream}
                }
            }
        }
        variant = "AppStream-8.0.0"
        p = ProductsFactory(label=self.product_label, version="8.0.0", variant=variant)
        m = ModulesFactory(name=self.module_name, stream=self.module_stream)
        t = TreesFactory()
        t.products.append(p)
        t.modules.append(m)

        r = client.get(self.path)
        assert r.status_code == 200
        assert r.get_json() == {variant: [t.arch]}

    @patch("product_listings_manager.products.getModuleProductListings")
    def test_product_listings_not_found(self, mock_get_module_product_listings, client):
        error_message = "NOT FOUND"
        mock_get_module_product_listings.side_effect = (
            products.ProductListingsNotFoundError(error_message)
        )
        r = client.get(self.path)
        assert r.status_code == 404
        assert error_message in r.get_json().get("message", "")

    @patch("product_listings_manager.products.getModuleProductListings")
    @patch("product_listings_manager.utils.log_remote_call_error")
    def test_unknown_error(self, mock_log, mock_getlistings, client):
        mock_getlistings.side_effect = Exception("Unexpected error")
        r = client.get(self.path)
        assert r.status_code == 500
        mock_log.assert_called_once_with(
            "API call getModuleProductListings() failed", self.product_label, self.nvr
        )


class TestLabels(object):
    @patch("product_listings_manager.products.getProductLabels")
    @patch("product_listings_manager.utils.log_remote_call_error")
    def test_unknown_error(self, mock_log, mock_getlabels, client):
        mock_getlabels.side_effect = Exception("Unexpected error")
        r = client.get("/api/v1.0/product-labels")
        assert r.status_code == 500
        mock_log.assert_called_once_with("API call getProductLabels() failed")

    def test_get_product_lables(self, client):
        p1 = ProductsFactory()
        p2 = ProductsFactory()
        r = client.get("/api/v1.0/product-labels")
        assert r.status_code == 200
        assert r.get_json() == [{"label": p1.label}, {"label": p2.label}]
