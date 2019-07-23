from mock import patch

from product_listings_manager import products


class TestIndex(object):
    def test_get_index(self, client):
        r = client.get('/api/v1.0/')
        expected_json = {
            'about_url': 'http://localhost/api/v1.0/about',
            'health_url': 'http://localhost/api/v1.0/health',
            'module_product_listings_url': 'http://localhost/api/v1.0/module-product-listings/:label/:module_build_nvr',
            'product_info_url': 'http://localhost/api/v1.0/product-info/:label',
            'product_listings_url': 'http://localhost/api/v1.0/product-listings/:label/:build_info',
            'product_labels_url': 'http://localhost/api/v1.0/product-labels',
        }
        assert r.status_code == 200
        assert r.get_json() == expected_json


class TestAbout(object):
    def test_get_version(self, client):
        from product_listings_manager import __version__
        r = client.get('/api/v1.0/about')
        assert r.status_code == 200
        assert r.get_json() == {'version': __version__}


class TestHealth(object):
    def test_health_db_fail(self, client):
        r = client.get('/api/v1.0/health')
        assert r.status_code == 503
        data = r.get_json()
        assert data['ok'] is False
        assert 'DB Error:' in data['message']

    @patch('product_listings_manager.rest_api_v1.db')
    @patch('product_listings_manager.rest_api_v1.products.get_koji_session')
    def test_health_koji_fail(self, mock_koji, mock_db, client):
        mock_db.return_value.engine.return_value.execute.return_value = 1
        mock_koji.side_effect = Exception('koji connect error')
        r = client.get('/api/v1.0/health')
        assert r.status_code == 503
        data = r.get_json()
        assert data['ok'] is False
        assert 'Koji Error: koji connect error' in data['message']

    @patch('product_listings_manager.rest_api_v1.db')
    @patch('product_listings_manager.rest_api_v1.products.get_koji_session')
    def test_health_ok(self, mock_koji, mock_db, client):
        mock_db.return_value.engine.return_value.execute.return_value = 1
        mock_koji.return_value.getAPIVersion.return_value = 1
        r = client.get('/api/v1.0/health')
        assert r.status_code == 200
        assert r.get_json() == {'ok': True, 'message': 'It works!'}


class TestProductInfo(object):
    product_label = 'RHEL-6-Server-EXTRAS-6'
    product_info_data = ['6.9', ['EXTRAS-6']]
    path = '/api/v1.0/product-info/{0}'.format(product_label)

    @patch('product_listings_manager.products.getProductInfo', return_value=product_info_data)
    def test_get_product_info(self, mock_get_product_info, client):
        r = client.get(self.path)
        assert r.status_code == 200
        assert r.get_json() == mock_get_product_info.return_value

    @patch('product_listings_manager.products.getProductInfo')
    def test_label_not_found(self, mock_getinfo, client):
        msg = 'Could not find a product with label: %s' % self.product_label
        mock_getinfo.side_effect = products.ProductListingsNotFoundError(msg)
        r = client.get(self.path)
        assert r.status_code == 404
        assert msg in r.get_json()['message']

    @patch('product_listings_manager.products.getProductInfo')
    @patch('product_listings_manager.utils.log_remote_call_error')
    def test_unknown_error(self, mock_log, mock_getinfo, client):
        mock_getinfo.side_effect = Exception('Unexpected error')
        r = client.get(self.path)
        assert r.status_code == 500
        mock_log.assert_called_once_with('API call getProductInfo() failed', self.product_label)


class TestProductListings(object):
    product_label = 'RHEL-6-Server-EXTRAS-6'
    nvr = 'dumb-init-1.2.0-1.20170802gitd283f8a.el6'
    product_listings_data = {
        'EXTRAS-6': {
            nvr: {
                'src': ['x86_64'], 'x86_64': ['x86_64']
            }
        }
    }
    path = '/api/v1.0/product-listings/{0}/{1}'.format(product_label, nvr)

    @patch('product_listings_manager.products.getProductListings', return_value=product_listings_data)
    def test_get_product_listings(self, mock_get_product_listings, client):
        r = client.get(self.path)
        assert r.status_code == 200
        assert r.get_json() == mock_get_product_listings.return_value

    @patch('product_listings_manager.products.getProductListings')
    def test_product_listings_not_found(self, mock_get_product_listings, client):
        error_message = 'NOT FOUND'
        mock_get_product_listings.side_effect = products.ProductListingsNotFoundError(error_message)
        r = client.get(self.path)
        assert r.status_code == 404
        assert r.get_json() == {'message': error_message}

    @patch('product_listings_manager.products.getProductListings')
    @patch('product_listings_manager.utils.log_remote_call_error')
    def test_unknown_error(self, mock_log, mock_getlistings, client):
        mock_getlistings.side_effect = Exception('Unexpected error')
        r = client.get(self.path)
        assert r.status_code == 500
        mock_log.assert_called_once_with('API call getProductListings() failed', self.product_label, self.nvr)


class TestModuleProductListings(object):
    product_label = 'RHEL-8.0.0'
    nvr = 'ruby-2.5-820181217154935.9edba152'
    product_listings_data = {
        'AppStream-8.0.0': ['x86_64']
    }
    path = '/api/v1.0/module-product-listings/{0}/{1}'.format(product_label, nvr)

    @patch('product_listings_manager.products.getModuleProductListings', return_value=product_listings_data)
    def test_get_module_product_listings(self, mock_get_module_product_listings, client):
        r = client.get(self.path)
        assert r.status_code == 200
        assert r.get_json() == mock_get_module_product_listings.return_value

    @patch('product_listings_manager.products.getModuleProductListings')
    def test_product_listings_not_found(self, mock_get_module_product_listings, client):
        error_message = 'NOT FOUND'
        mock_get_module_product_listings.side_effect = products.ProductListingsNotFoundError(error_message)
        r = client.get(self.path)
        assert r.status_code == 404
        assert error_message in r.get_json().get('message', '')

    @patch('product_listings_manager.products.getModuleProductListings')
    @patch('product_listings_manager.utils.log_remote_call_error')
    def test_unknown_error(self, mock_log, mock_getlistings, client):
        mock_getlistings.side_effect = Exception('Unexpected error')
        r = client.get(self.path)
        assert r.status_code == 500
        mock_log.assert_called_once_with('API call getModuleProductListings() failed', self.product_label, self.nvr)


class TestLabels(object):
    labels = [
        {'label': 'RHEL-5'},
        {'label': 'RHEL-6'}
    ]

    @patch('product_listings_manager.products.getProductLabels', return_value=labels)
    def test_get_product_info(self, mock_get_product_info, client):
        r = client.get('/api/v1.0/product-labels')
        assert r.status_code == 200
        assert r.get_json() == mock_get_product_info.return_value

    @patch('product_listings_manager.products.getProductLabels')
    @patch('product_listings_manager.utils.log_remote_call_error')
    def test_unknown_error(self, mock_log, mock_getlabels, client):
        mock_getlabels.side_effect = Exception('Unexpected error')
        r = client.get('/api/v1.0/product-labels')
        assert r.status_code == 500
        mock_log.assert_called_once_with('API call getProductLabels() failed')
