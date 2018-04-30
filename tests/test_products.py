from products import Products
from products import getProductInfo
from products import getProductListings
import pytest


pytestmark = pytest.mark.skipif(
    not pytest.config.getoption('--live'),
    reason='use --live argument to query production servers'
)

@pytest.fixture(scope='module')
def dbh():
    return Products.compose_get_dbh()


class TestProductLive(object):

    def test_score(self):
        # release = ???
        # assert Products.score(release) = ???
        pass

    def test_my_sort(self):
        # x, y = (???, ???)
        # assert Products.my_sort(x, y) == ???
        pass

    def test_execute_query(self):
        # assert Products.execute_query('FOO')
        # assert Products.execute_query('FOO', args)
        pass

    def test_get_product_info(self, dbh):
        product = 'RHEL-6-Server-EXTRAS-6'
        result = Products.get_product_info(dbh, product)
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


class TestGetProductInfo(object):

    def test_simple(self):
        label = 'RHEL-6-Server-EXTRAS-6'
        result = getProductInfo(label)
        assert result == ('6.9', ['EXTRAS-6'])


class TestGetProductListings(object):

    def test_simple(self):
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
