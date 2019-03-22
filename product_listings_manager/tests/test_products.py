from product_listings_manager.app import create_app
from product_listings_manager.products import Products
from product_listings_manager.products import getProductInfo
from product_listings_manager.products import getProductListings
from product_listings_manager.products import getModuleProductListings
from product_listings_manager.products import getProductLabels
import pytest


pytestmark = pytest.mark.skipif(
    not pytest.config.getoption('--live', default=False),
    reason='use --live argument to query production servers'
)


@pytest.fixture(scope='module')
def app():
    app = create_app()
    with app.app_context():
        yield app


class TestProductLive(object):

    def test_score(self):
        # release = ???
        # assert Products.score(release) = ???
        pass

    def test_my_sort(self):
        # x, y = (???, ???)
        # assert Products.my_sort(x, y) == ???
        pass

    def test_get_product_info(self, app):
        product = 'RHEL-6-Server-EXTRAS-6'
        result = Products.get_product_info(product)
        assert result == ('6.9', ['EXTRAS-6'])

    def test_get_overrides(self):
        pass

    def test_get_match_versions(self):
        pass

    def test_get_srconly_flag(self):
        pass

    def test_precalc_treelist(self):
        pass

    def test_dest_get_archs(self):
        pass

    def test_get_module(self):
        pass

    def test_get_module_overrides(self):
        pass

    def test_precalc_module_trees(self):
        pass


class TestGetProductInfo(object):

    def test_simple(self, app):
        label = 'RHEL-6-Server-EXTRAS-6'
        result = getProductInfo(label)
        assert result == ('6.9', ['EXTRAS-6'])


class TestGetProductListings(object):

    def test_simple(self, app):
        label = 'RHEL-6-Server-EXTRAS-6'
        build = 'dumb-init-1.2.0-1.20170802gitd283f8a.el6'
        result = getProductListings(label, build)
        expected = \
            {'EXTRAS-6':
             {'dumb-init-1.2.0-1.20170802gitd283f8a.el6':
              {'src': ['x86_64'], 'x86_64': ['x86_64']},
              'dumb-init-debuginfo-1.2.0-1.20170802gitd283f8a.el6':
              {'x86_64': ['x86_64']},
              }
             }
        assert result == expected


class TestGetModuleProductListings(object):

    def test_getModuleProductListings(self, app):
        label = 'RHEL-8.0.0'
        module = 'ruby-2.5-820190111110530.9edba152'
        result = getModuleProductListings(label, module)
        expected = {
            'AppStream-8.0.0': ['aarch64', 'ppc64le', 's390x', 'x86_64']
        }
        assert result == expected


class TestProductLabels(object):

    def test_getProductLabels(self, app):
        result = getProductLabels()
        assert len(result) > 1200
        assert {'label': 'RHEL-6'} in result
        assert {'label': 'RHEL-6-Client'} in result
        assert {'label': 'RHEL-6-Server'} in result
