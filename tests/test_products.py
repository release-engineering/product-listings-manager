from unittest.mock import patch

import pytest

from product_listings_manager.models import MatchVersions as MatchVersionsModel
from product_listings_manager.models import (
    ModuleOverrides as ModuleOverridesModel,
)
from product_listings_manager.models import Overrides as OverridesModel
from product_listings_manager.models import Products as ProductsModel
from product_listings_manager.models import Trees as TreesModel
from product_listings_manager.products import (
    ProductListingsNotFoundError,
    get_match_versions,
    get_module_overrides,
    get_module_product_listings,
    get_overrides,
    get_product_info,
    get_product_labels,
    get_product_listings,
    my_sort,
    precalc_treelist,
    score,
)


@pytest.fixture
def db():
    with patch("product_listings_manager.models.SessionLocal", autospec=True) as mocked:
        yield mocked()


class TestProduct:
    def test_score(self):
        assert 0 == score("Test1")
        assert 1 == score("alpha")
        assert 2 == score("BETA3")
        assert 3 == score("rc")
        assert 4 == score("Gold")
        assert 5 == score("U5")
        assert 5 == score("U1-beta")
        assert -1 == score("other")

    def test_my_sort(self):
        # x starts with y
        assert -1 == my_sort("U1-beta", "U1")

        # y starts with x
        assert 1 == my_sort("U1", "U1-beta")

        # score(x) == score(y)
        assert -1 == my_sort("7.1", "7.2")
        assert -1 == my_sort("U3", "U4")
        assert 1 == my_sort("7.2", "7.1")
        assert 1 == my_sort("U4", "U3")
        assert 0 == my_sort("8.0.0", "8.0.0")

        # score(x) != score(y)
        assert -1 == my_sort("Beta1", "Gold")
        assert 1 == my_sort("6.9", "6.3")
        assert 1 == my_sort("8.1", "8.0.0")

    def test_get_product_info(self, db):
        label = "RHEL-7"
        db.query(ProductsModel).filter_by.return_value.all.return_value = [
            ProductsModel(id=1, label=label, version="7.2", variant="Server"),
            ProductsModel(id=2, label=label, version="7.3", variant="Server"),
            ProductsModel(id=3, label=label, version="7.4", variant="Server"),
            ProductsModel(id=4, label=label, version="7.4", variant="Client"),
        ]
        result = get_product_info(db, label)
        assert result == ("7.4", ["Server", "Client"])

    def test_get_product_info_not_found(self, db):
        db.query(ProductsModel).filter_by.return_value.all.return_value = []
        label = "Fake-label"
        with pytest.raises(ProductListingsNotFoundError) as excinfo:
            get_product_info(db, label)
        assert f"Could not find a product with label: {label}" == str(excinfo.value)

    def test_get_overrides(self, db):
        label = "RHEL-7"
        version = "7.5"
        mock_join = db.query(OverridesModel).join.return_value
        mock_join.filter.return_value.all.return_value = [
            OverridesModel(
                name="fake",
                pkg_arch="src",
                product_arch="x86_64",
                include=True,
            ),
            OverridesModel(
                name="fake", pkg_arch="src", product_arch="ppc64", include=True
            ),
            OverridesModel(
                name="fake",
                pkg_arch="x86_64",
                product_arch="x86_64",
                include=False,
            ),
        ]
        assert get_overrides(db, label, version) == {
            "fake": {
                "src": {"ppc64": True, "x86_64": True},
                "x86_64": {"x86_64": False},
            }
        }

    def test_get_match_versions(self, db):
        product = "fake-product"
        mock_filter_by = db.query(MatchVersionsModel).filter_by.return_value
        mock_filter_by.all.return_value = [
            MatchVersionsModel(name="fake1"),
            MatchVersionsModel(name="fake2"),
        ]
        assert get_match_versions(db, product) == ["fake1", "fake2"]

    def test_get_srconly_flag(self):
        pass

    def test_precalc_treelist(self, db):
        mock_join = db.query(TreesModel).join.return_value
        mock_join_order_by = mock_join.order_by.return_value
        mock_join_order_by.filter.return_value.filter.return_value.all.return_value = [
            TreesModel(id=3, arch="x86_64"),
            TreesModel(id=2, arch="x86_64"),
            TreesModel(id=1, arch="ppc64"),
        ]
        assert sorted(precalc_treelist(db, "fake-product", "7.5", "Server")) == sorted(
            [1, 3]
        )

    def test_dest_get_archs(self):
        pass

    def test_get_module_overrides(self, db):
        module_name = "perl"
        module_stream = "5.24"
        mock_join = db.query(ModuleOverridesModel).join.return_value
        mock_join.filter.return_value.filter.return_value.all.return_value = [
            ModuleOverridesModel(
                name=module_name,
                stream=module_stream,
                product=1,
                product_arch="x86_64",
            ),
            ModuleOverridesModel(
                name=module_name,
                stream=module_stream,
                product=1,
                product_arch="ppc64le",
            ),
            ModuleOverridesModel(
                name=module_name,
                stream=module_stream,
                product=1,
                product_arch="s390x",
            ),
        ]
        assert get_module_overrides(
            db, "fake", "fake", module_name, module_stream, "fake"
        ) == ["x86_64", "ppc64le", "s390x"]

    def test_get_product_labels(self, db):
        mock_with_entities = db.query(ProductsModel).with_entities.return_value
        mock_with_entities.distinct.return_value.all.return_value = [
            ProductsModel(label="label1"),
            ProductsModel(label="label2"),
        ]
        assert get_product_labels(db) == [
            {"label": "label1"},
            {"label": "label2"},
        ]


class TestGetProductListings:
    @patch("product_listings_manager.products.get_koji_session")
    def test_rpms_not_found(self, mock_get_koji_session, db):
        mock_get_koji_session.return_value.listRPMs.return_value = []
        build = "fake-build-1.0-1.el6"
        with pytest.raises(ProductListingsNotFoundError) as excinfo:
            get_product_listings(db, "fake-label", build)
        assert f"Could not find any RPMs for build: {build}" == str(excinfo.value)


class TestGetModuleProductListings:
    @patch("product_listings_manager.products.get_build")
    def test_not_module_build(self, mock_get_build, db):
        mock_get_build.return_value = {"name": "perl"}
        nvr = "perl-5.16.3-1.el7"
        with pytest.raises(ProductListingsNotFoundError) as excinfo:
            get_module_product_listings(db, "fake-label", nvr)
        assert f"This is not a module build: {nvr}" == str(excinfo.value)

    @patch("product_listings_manager.products.get_module_overrides")
    @patch("product_listings_manager.products.get_product_info")
    @patch("product_listings_manager.products.precalc_treelist")
    @patch("product_listings_manager.products.get_build")
    def test_get_module_product_listings(
        self,
        mock_get_build,
        mock_precalc_treelist,
        mock_get_product_info,
        mock_get_module_overrides,
        db,
    ):
        mock_with_entities = db.query(TreesModel).with_entities.return_value
        mock_with_entities.join.return_value.filter.return_value.filter.return_value = [
            ("x86_64",),
        ]
        nvr = "perl-5.24-8010020190529084201.3af8e029"
        mock_get_product_info.return_value = ("8.0", ["AppStream-8.0"])

        # test without overrides
        mock_get_module_overrides.return_value = []
        assert get_module_product_listings(db, "fake-label", nvr) == {
            "AppStream-8.0": ["x86_64"]
        }

        # test with overrides
        mock_get_module_overrides.return_value = ["ppc64le"]
        assert get_module_product_listings(db, "fake-label", nvr) == {
            "AppStream-8.0": ["ppc64le", "x86_64"]
        }
