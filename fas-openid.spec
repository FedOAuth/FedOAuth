Name:           fas-openid
Version:        1.2
Release:        1%{?dist}
Summary:        An OpenID provider which authenticates users against FAS

License:        GPLv2+
URL:            https://github.com/fedora-infra/%{name}
Source0:        https://fedorahosted.org/releases/f/a/%{name}/%{name}-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  python-setuptools
BuildRequires:  python-setuptools-devel
BuildRequires:  python-devel
BuildRequires:  python-flask
BuildRequires:  python-fedora
BuildRequires:  python-fedora-flask
BuildRequires:  python-flask-babel
BuildRequires:  python-sqlalchemy0.7
BuildRequires:  python-flask-sqlalchemy
BuildRequires:  python-openid
BuildRequires:  python-openid-teams
BuildRequires:  python-openid-cla
BuildRequires:  python-beaker
Requires:       python-sqlalchemy0.7
Requires:       python-flask
Requires:       python-fedora
Requires:       python-fedora-flask
Requires:       python-flask-babel
Requires:       python-flask-sqlalchemy
Requires:       python-beaker
Requires:       python-openid
Requires:       python-openid-teams
Requires:       python-openid-cla
Requires:       mod_wsgi
Requires:       httpd
Requires(pre):  shadow-utils

%description
FAS-OpenID is an OpenID provider which gets it's information from Fedora Account System (FAS).

%prep
%setup -q


%build
%{__python} setup.py build

%install
%{__python} setup.py install --skip-build --install-data=%{_datadir} --root %{buildroot}

%{__mkdir_p} %{buildroot}%{_sysconfdir}/%{name}
%{__mkdir_p} %{buildroot}%{_sysconfdir}/httpd/conf.d
%{__mkdir_p} %{buildroot}%{_datadir}/%{name}
%{__mkdir_p} %{buildroot}%{_datadir}/%{name}/static

%{__install} -m 644 fas_openid.conf %{buildroot}%{_sysconfdir}/httpd/conf.d/fas_openid.conf
%{__install} -m 644 fas_openid/static/* %{buildroot}%{_datadir}/%{name}/static
%{__install} -m 644 %{name}.cfg.sample %{buildroot}%{_sysconfdir}/%{name}/%{name}.cfg
%{__install} -m 644 createdb.py %{buildroot}%{_datadir}/%{name}/createdb.py
%{__install} -m 644 %{name}.wsgi %{buildroot}%{_datadir}/%{name}/%{name}.wsgi

%pre
getent group fas-openid >/dev/null || groupadd -r fas-openid
getent passwd fas-openid >/dev/null || \
    useradd -r -g fas-openid -d %{_datadir}/%{name} -s /sbin/nologin \
    -c "Account used for FAS-OpenID serving" fas-openid
exit 0

%files
%doc
%dir %{_sysconfdir}/%{name}
%config(noreplace) %{_sysconfdir}/%{name}/%{name}.cfg
%config(noreplace) %{_sysconfdir}/httpd/conf.d/fas_openid.conf
%{_datadir}/%{name}
%{python_sitelib}/*

%changelog
* Sat Jun 01 2013 Patrick Uiterwijk <puiterwijk@gmail.com> - 1.2-1
- Migrated the openid teams module to python-openid-teams
- Migrated the openid cla module to python-openid-cla

* Wed May 01 2013 Patrick Uiterwijk <puiterwijk@gmail.com> - 1.1.1-1
- Update URL to fonts to https

* Wed May 01 2013 Patrick Uiterwijk <puiterwijk@gmail.com> - 1.1.0-1
- Split auth system from the core code
- Add a button for user creation to the login screen
- Fixed an issue which made some browsers give a warning about posting the approval form to http
- Cleaned up the code to be pep8-compliant

* Tue Mar 05 2013 Patrick Uiterwijk <puiterwijk@gmail.com> - 1.0.0-1
- Launch version

* Sat Mar 02 2013 Patrick Uiterwijk <puiterwijk@gmail.com> - 0.6.5-1
- Only remember trust-root acceptance once

* Tue Feb 26 2013 Patrick Uiterwijk <puiterwijk@gmail.com> - 0.6.4-1
- Also install createdb.py

* Tue Feb 26 2013 Patrick Uiterwijk <puiterwijk@gmail.com> - 0.6.3-1
- Added some config file sanity checks

* Wed Feb 20 2013 Patrick Uiterwijk <puiterwijk@gmail.com> - 0.6.2-1
- Switched to beaker in sqlalchemy

* Wed Feb 20 2013 Patrick Uiterwijk <puiterwijk@gmail.com> - 0.6.1-1
- Corrected a mimetype issue

* Tue Feb 19 2013 Patrick Uiterwijk <puiterwijk@gmail.com> - 0.6.0-1
- Moved from flask_fas to FasProxyClient

* Mon Feb 18 2013 Patrick Uiterwijk <puiterwijk@gmail.com> - 0.5.2-1
- Fixed a re-post bug

* Mon Feb 18 2013 Patrick Uiterwijk <puiterwijk@gmail.com> - 0.5.1-1
- Added CSRF protection
- Fixed bug where trust_root is not shown on login page

* Fri Feb 15 2013 Patrick Uiterwijk <puiterwijk@gmail.com> - 0.5.0-1
- CLA extension imported
- Logging more parseable
- Template now using global layout

* Wed Feb 13 2013 Patrick Uiterwijk <puiterwijk@gmail.com> - 0.4.0-2
- Updated spec file to include the static dir

* Wed Feb 13 2013 Patrick Uiterwijk <puiterwijk@gmail.com> - 0.4.0-1
- Imported new template
- Primary PAPE implementation

* Sun Feb 10 2013 Patrick Uiterwijk <puiterwijk@gmail.com> - 0.3.0-1
- Now fully OpenID 2.0 compliant by saving POST values withing an session

* Fri Feb 08 2013 Patrick Uiterwijk <puiterwijk@gmail.com> - 0.2.0-1
- Added a special team name to request all groups a user is a member of

* Sat Feb 02 2013 Patrick Uiterwijk <puiterwijk@gmail.com> - 0.1.5-1
- We now also log the trust_root for succesful OpenID claimings

* Thu Jan 31 2013 Patrick Uiterwijk <puiterwijk@gmail.com> - 0.1.4-2
- Marked config files as noreplace

* Thu Jan 31 2013 Patrick Uiterwijk <puiterwijk@gmail.com> - 0.1.4-1
- Removed the Login HTTPS requirement from the .conf

* Wed Jan 30 2013 Patrick Uiterwijk <puiterwijk@gmail.com> - 0.1.3-1
- Fixed key name in default configuration file
- Mark fas-openid.cfg and fas_openid.conf as config files

* Tue Jan 29 2013 Patrick Uiterwijk <puiterwijk@gmail.com> - 0.1.2-1
- Fixed the SQLAlchemy import for flask-sqlalchemy

* Tue Jan 29 2013 Patrick Uiterwijk <puiterwijk@gmail.com> - 0.1.1-1
- Added account creation in the RPM
- Fixed the SQLAlchemy imports to be >= 0.7
