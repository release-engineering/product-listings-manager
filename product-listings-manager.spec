%if 0%{?rhel} && 0%{?rhel} <= 7
%bcond_with python3
%else
%bcond_without python3
%endif

%global modname product_listings_manager

Name: product-listings-manager
Version: 0.3.0
Release: 1%{?dist}
Summary: HTTP interface to composedb

License: MIT
URL: https://github.com/release-engineering/product-listings-manager
Source0: %{name}-%{version}.tar.gz
BuildArch: noarch

%if %{with python3}
BuildRequires: python3-devel
BuildRequires: python3-flask
BuildRequires: python3-flask-xml-rpc
BuildRequires: python3-flask-restful
BuildRequires: python3-koji
BuildRequires: python3-pygresql
BuildRequires: python3-pytest
BuildRequires: python3-mock
Requires: python3-flask
Requires: python3-flask-xml-rpc
Requires: python3-flask-restful
Requires: python3-koji
Requires: python3-pygresql
%else
BuildRequires: python2-devel
BuildRequires: python-flask
BuildRequires: python-flask-xml-rpc
BuildRequires: python2-flask-restful
BuildRequires: python2-koji
BuildRequires: PyGreSQL
BuildRequires: pytest
BuildRequires: python-mock
Requires: python-flask
Requires: python-flask-xml-rpc
Requires: python2-flask-restful
Requires: python2-koji
Requires: PyGreSQL
%endif

%description
HTTP interface for finding product listings and interacting with data in
composedb.

%prep
%autosetup


%build
%if %{with python3}
%py3_build
%else
%py2_build
%endif


%install
%if %{with python3}
%py3_install
%else
%py2_install
%endif
mkdir -p %{buildroot}%{_sysconfdir}/%{name}
cp -p %{modname}/config.py %{buildroot}%{_sysconfdir}/%{name}

%check
%if %{with python3}
py.test-3 -v %{modname}/tests
%else
py.test-2.7 -v %{modname}/tests
%endif

%files
%license LICENSE
%doc README.rst
%config(noreplace) %{_sysconfdir}/%{name}/config.py
%exclude %{_sysconfdir}/%{name}/config.pyc
%exclude %{_sysconfdir}/%{name}/config.pyo
%if %{with python3}
%{python3_sitelib}/%{modname}/
%{python3_sitelib}/%{modname}-*.egg-info/
%else
%{python2_sitelib}/%{modname}/
%{python2_sitelib}/%{modname}-*.egg-info/
%endif

%changelog
* Wed Feb 13 2019 Haibo Lin <hlin@redhat.com> 0.3.0-1
- openshift: Change health check path (hlin@redhat.com)
- Fix product listings not found error (hluk@email.cz)
- Follow flake8 convention (hlin@redhat.com)
- Add module product listings REST API (hlin@redhat.com)
- Fix HTTP 404 response code (hluk@email.cz)
- Log remote IP, traceback and arguments of remote call on error
  (hluk@email.cz)
- add database documentation (kdreyer@redhat.com)

* Tue Jul 03 2018 Lukas Holecek <lholecek@redhat.com> 0.2.0-1
- Use sanitized SQL queries (lholecek@redhat.com)
- drop optional FLASK_CONFIG during tests and packaging (kdreyer@redhat.com)
- handle HTTP requests to "/api/v1.0/" (kdreyer@redhat.com)
- handle HTTP requests to "/" (kdreyer@redhat.com)
- JSON responses for 404 errors (kdreyer@redhat.com)
- optionally load config from /etc or from FLASK_CONFIG (kdreyer@redhat.com)
- Add support for mod_wsgi (lholecek@redhat.com)
- set products.py posgres connection from Flask config (kdreyer@redhat.com)
- Add REST API and split to multiple python submodules (lholecek@redhat.com)
- switch to Flask-XML-RPC dependency (kdreyer@redhat.com)
- add tests (kdreyer@redhat.com)
- add README (kdreyer@redhat.com)
- products.py: use "WHERE variable = ANY(ARRAY...)" (kdreyer@redhat.com)
