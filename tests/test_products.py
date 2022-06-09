import pytest
from mock import patch

from product_listings_manager.app import create_app
from product_listings_manager.models import MatchVersions as MatchVersionsModel
from product_listings_manager.models import ModuleOverrides as ModuleOverridesModel
from product_listings_manager.models import Products as ProductsModel
from product_listings_manager.models import Overrides as OverridesModel
from product_listings_manager.models import Trees as TreesModel
from product_listings_manager.products import Products
from product_listings_manager.products import ProductListingsNotFoundError
from product_listings_manager.products import getProductInfo
from product_listings_manager.products import getProductListings
from product_listings_manager.products import getModuleProductListings
from product_listings_manager.products import getProductLabels


@pytest.fixture(scope="module")
def app():
    app = create_app()
    with app.app_context():
        yield app


class TestProduct(object):
    def test_score(self):
        assert 0 == Products.score("Test1")
        assert 1 == Products.score("alpha")
        assert 2 == Products.score("BETA3")
        assert 3 == Products.score("rc")
        assert 4 == Products.score("Gold")
        assert 5 == Products.score("U5")
        assert 5 == Products.score("U1-beta")
        assert -1 == Products.score("other")

    def test_my_sort(self):
        # x starts with y
        assert -1 == Products.my_sort("U1-beta", "U1")

        # y starts with x
        assert 1 == Products.my_sort("U1", "U1-beta")

        # score(x) == score(y)
        assert -1 == Products.my_sort("7.1", "7.2")
        assert -1 == Products.my_sort("U3", "U4")
        assert 1 == Products.my_sort("7.2", "7.1")
        assert 1 == Products.my_sort("U4", "U3")
        assert 0 == Products.my_sort("8.0.0", "8.0.0")

        # score(x) != score(y)
        assert -1 == Products.my_sort("Beta1", "Gold")
        assert 1 == Products.my_sort("6.9", "6.3")
        assert 1 == Products.my_sort("8.1", "8.0.0")

    @patch("product_listings_manager.products.models.Products")
    def test_get_product_info(self, mock_products_model):
        label = "RHEL-7"
        mock_products_model.query.filter_by.return_value.all.return_value = [
            ProductsModel(id=1, label=label, version="7.2", variant="Server"),
            ProductsModel(id=2, label=label, version="7.3", variant="Server"),
            ProductsModel(id=3, label=label, version="7.4", variant="Server"),
            ProductsModel(id=4, label=label, version="7.4", variant="Client"),
        ]
        result = Products.get_product_info(label)
        assert result == ("7.4", ["Server", "Client"])

    @patch("product_listings_manager.products.models.Products")
    def test_get_product_info_not_found(self, mock_products_model):
        mock_products_model.query.filter_by.return_value.all.return_value = []
        label = "Fake-label"
        with pytest.raises(ProductListingsNotFoundError) as excinfo:
            Products.get_product_info(label)
        assert "Could not find a product with label: {}".format(label) == str(
            excinfo.value
        )

    @patch("product_listings_manager.products.models.Overrides")
    def test_get_overrides(self, mock_overrides_model):
        label = "RHEL-7"
        version = "7.5"
        mock_overrides_model.query.join.return_value.filter.return_value.all.return_value = [
            OverridesModel(
                name="fake", pkg_arch="src", product_arch="x86_64", include=True
            ),
            OverridesModel(
                name="fake", pkg_arch="src", product_arch="ppc64", include=True
            ),
            OverridesModel(
                name="fake", pkg_arch="x86_64", product_arch="x86_64", include=False
            ),
        ]
        assert Products.get_overrides(label, version) == {
            "fake": {
                "src": {"ppc64": True, "x86_64": True},
                "x86_64": {"x86_64": False},
            }
        }

    @patch("product_listings_manager.products.models.MatchVersions")
    def test_get_match_versions(self, mock_matchversions_model):
        product = "fake-product"
        mock_matchversions_model.query.filter_by.return_value.all.return_value = [
            MatchVersionsModel(name="fake1"),
            MatchVersionsModel(name="fake2"),
        ]
        assert Products.get_match_versions(product) == ["fake1", "fake2"]

    def test_get_srconly_flag(self):
        pass

    @patch("product_listings_manager.products.models.Trees")
    def test_precalc_treelist(self, mock_trees_model):
        mock_trees_model.query.join.return_value.order_by.return_value.filter.return_value.filter.return_value.all.return_value = [
            TreesModel(id=3, arch="x86_64"),
            TreesModel(id=2, arch="x86_64"),
            TreesModel(id=1, arch="ppc64"),
        ]
        assert sorted(
            Products.precalc_treelist("fake-product", "7.5", "Server")
        ) == sorted([1, 3])

    def test_dest_get_archs(self):
        pass

    @patch("product_listings_manager.products.models.ModuleOverrides")
    def test_get_module_overrides(self, mock_moduleoverrides_model):
        module_name = "perl"
        module_stream = "5.24"
        mock_moduleoverrides_model.query.join.return_value.filter.return_value.filter.return_value.all.return_value = [
            ModuleOverridesModel(
                name=module_name, stream=module_stream, product=1, product_arch="x86_64"
            ),
            ModuleOverridesModel(
                name=module_name,
                stream=module_stream,
                product=1,
                product_arch="ppc64le",
            ),
            ModuleOverridesModel(
                name=module_name, stream=module_stream, product=1, product_arch="s390x"
            ),
        ]
        assert Products.get_module_overrides(
            "fake", "fake", module_name, module_stream, "fake"
        ) == ["x86_64", "ppc64le", "s390x"]

    @patch("product_listings_manager.products.models.Products")
    def test_get_product_labels(self, mock_products_model):
        mock_products_model.query.with_entities.return_value.distinct.return_value.all.return_value = [
            ProductsModel(label="label1"),
            ProductsModel(label="label2"),
        ]
        assert Products.get_product_labels() == [
            {"label": "label1"},
            {"label": "label2"},
        ]


class TestGetProductInfo(object):
    @patch("product_listings_manager.products.Products.get_product_info")
    def test_getProductInfo(self, mock_get_product_info):
        label = "Fake-label"
        getProductInfo(label)
        mock_get_product_info.assert_called_once_with(label)


class TestGetProductListings(object):
    @patch("product_listings_manager.products.get_koji_session")
    def test_rpms_not_found(self, mock_get_koji_session):
        mock_get_koji_session.return_value.listRPMs.return_value = []
        build = "fake-build-1.0-1.el6"
        with pytest.raises(ProductListingsNotFoundError) as excinfo:
            getProductListings("fake-label", build)
        assert "Could not find any RPMs for build: {}".format(build) == str(
            excinfo.value
        )


class TestGetModuleProductListings(object):
    @patch("product_listings_manager.products.get_build")
    def test_not_module_build(self, mock_get_build):
        mock_get_build.return_value = {"name": "perl"}
        nvr = "perl-5.16.3-1.el7"
        with pytest.raises(ProductListingsNotFoundError) as excinfo:
            getModuleProductListings("fake-label", nvr)
        assert "It's not a module build: {}".format(nvr) == str(excinfo.value)

    @patch("product_listings_manager.products.Products.get_module_overrides")
    @patch("product_listings_manager.products.Products.get_product_info")
    @patch("product_listings_manager.products.Products.precalc_treelist")
    @patch("product_listings_manager.products.get_build")
    @patch("product_listings_manager.products.models.Trees")
    def test_getModuleProductListings(
        self,
        mock_trees_model,
        mock_get_build,
        mock_precalc_treelist,
        mock_get_product_info,
        mock_get_module_overrides,
    ):
        mock_trees_model.query.with_entities.return_value.join.return_value.filter.return_value.filter.return_value = [
            ("x86_64",),
        ]
        nvr = "perl-5.24-8010020190529084201.3af8e029"
        mock_get_product_info.return_value = ("8.0", ["AppStream-8.0"])

        # test without overrides
        mock_get_module_overrides.return_value = []
        assert getModuleProductListings("fake-label", nvr) == {
            "AppStream-8.0": ["x86_64"]
        }

        # test with overrides
        mock_get_module_overrides.return_value = ["ppc64le"]
        assert getModuleProductListings("fake-label", nvr) == {
            "AppStream-8.0": ["ppc64le", "x86_64"]
        }


class TestProductLabels(object):
    @patch("product_listings_manager.products.Products.get_product_labels")
    def test_getProductLabels(self, mock_get_product_labels):
        getProductLabels()
        mock_get_product_labels.assert_called_once_with()
