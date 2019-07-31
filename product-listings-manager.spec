%global modname product_listings_manager

Name: product-listings-manager
Version: 1.1.0
Release: 1%{?dist}
Summary: HTTP interface to composedb

License: MIT
URL: https://github.com/release-engineering/product-listings-manager
Source0: %{name}-%{version}.tar.gz
BuildArch: noarch

BuildRequires: python3-devel
BuildRequires: python3-flask
BuildRequires: python3-flask-sqlalchemy
BuildRequires: python3-flask-restful
BuildRequires: python3-koji
BuildRequires: python3-psycopg2
BuildRequires: python3-setuptools
BuildRequires: python3-sqlalchemy
Requires: koji
Requires: python3-flask
Requires: python3-flask-sqlalchemy
Requires: python3-flask-restful
Requires: python3-koji
Requires: python3-psycopg2
Requires: python3-sqlalchemy

%description
HTTP interface for finding product listings and interacting with data in
composedb.

%prep
%autosetup

%build
%py3_build

%install
%py3_install
mkdir -p %{buildroot}%{_sysconfdir}/%{name}
cp -p %{modname}/config.py %{buildroot}%{_sysconfdir}/%{name}

%files
%license LICENSE
%doc README.rst
%config(noreplace) %{_sysconfdir}/%{name}/config.py
%exclude %{_sysconfdir}/%{name}/config.pyc
%exclude %{_sysconfdir}/%{name}/config.pyo
%{python3_sitelib}/%{modname}/
%{python3_sitelib}/%{modname}-*.egg-info/

%changelog
* Mon Jul 01 2019 Haibo Lin <hlin@redhat.com> 1.1.0-1
- Query module overrides directly (hlin@redhat.com)
- Use fedora 29 instead of rawhide for py37 tests (hlin@redhat.com)
- Refactor get module product listings (hlin@redhat.com)
- Install new version of gunicorn in Docker container (hlin@redhat.com)

* Wed May 22 2019 Haibo Lin <hlin@redhat.com> 1.0.0-1
- Check koji status in health API (hlin@redhat.com)
- Add missing packages to Dockerfile (hlin@redhat.com)
- Generate coverage report (hlin@redhat.com)
- Support python3 (hlin@redhat.com)
- Add health check API (hlin@redhat.com)

* Thu Apr 11 2019 Haibo Lin <hlin@redhat.com> 0.5.0-1
- Change tito tag format to make it shorter (hlin@redhat.com)
- Modulize configuration (hlin@redhat.com)
- Replace raw SQL with SQLAlchemy models (hlin@redhat.com)
- Define models using SQLAlchemy (hlin@redhat.com)

* Tue Apr 09 2019 Haibo Lin <hlin@redhat.com> 0.4-1
- Don't ignore spec file changes in git (hluk@email.cz)
- Remove deprecated XML-RPC API (hluk@email.cz)
- Add REST API endpoint to list product labels (hluk@email.cz)
- Show image building status in quay.io (hlin@redhat.com)
- Shorten commit message of tito tag command (hlin@redhat.com)
- Configure logging for PLM (hlin@redhat.com)
- Use application factory (hlin@redhat.com)

* Mon Mar 18 2019 Haibo Lin <hlin@redhat.com> 0.3.3-1
- Use latest module record (hlin@redhat.com)
- Fix positive overrides ignored issue (hlin@redhat.com)

* Fri Mar 08 2019 Haibo Lin <hlin@redhat.com> 0.3.2-1
- Fix tests (hluk@email.cz)
- Get module builds based on name and stream only (lsedlar@redhat.com)

* Fri Feb 22 2019 Haibo Lin <hlin@redhat.com> 0.3.1-1
- Response 404 for module product listings not found error (hlin@redhat.com)

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
