# SPDX-License-Identifier: GPL-2.0+
import pytest

from product_listings_manager.products import (
    get_module_product_listings,
    get_product_info,
    get_product_labels,
    get_product_listings,
)


@pytest.mark.live
class TestProductLive:
    def test_get_product_info(self, app, db):
        product = "RHEL-6-Server-EXTRAS-6"
        result = get_product_info(db, product)
        assert result == ("6.9", ["EXTRAS-6"])


@pytest.mark.live
class TestGetProductInfo:
    def test_simple(self, app, db):
        label = "RHEL-6-Server-EXTRAS-6"
        result = get_product_info(db, label)
        assert result == ("6.9", ["EXTRAS-6"])


@pytest.mark.live
class TestGetProductListings:
    def test_simple(self, app, db):
        label = "RHEL-6-Server-EXTRAS-6"
        build = "dumb-init-1.2.0-1.20170802gitd283f8a.el6"
        result = get_product_listings(db, label, build)
        expected = {
            "EXTRAS-6": {
                "dumb-init-1.2.0-1.20170802gitd283f8a.el6": {
                    "src": ["x86_64"],
                    "x86_64": ["x86_64"],
                },
                "dumb-init-debuginfo-1.2.0-1.20170802gitd283f8a.el6": {
                    "x86_64": ["x86_64"]
                },
            }
        }
        assert result == expected


@pytest.mark.live
class TestGetModuleProductListings:
    def test_getModuleProductListings(self, app, db):
        label = "RHEL-8.0.0"
        module = "ruby-2.5-820190111110530.9edba152"
        result = get_module_product_listings(db, label, module)
        expected = {
            "AppStream-8.0.0": ["aarch64", "ppc64le", "s390x", "x86_64"]
        }
        assert result == expected


@pytest.mark.live
class TestProductLabels:
    def test_getProductLabels(self, app, db):
        result = get_product_labels(db)
        assert len(result) > 1200
        assert {"label": "RHEL-6"} in result
        assert {"label": "RHEL-6-Client"} in result
        assert {"label": "RHEL-6-Server"} in result
