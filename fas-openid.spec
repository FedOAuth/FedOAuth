Name:           fas-openid
Version:        0.1.1
Release:        1%{?dist}
Summary:        An OpenID provider which authenticates users against FAS

License:        GPLv2+
URL:            https://github.com/fedora-infra/%{name}
Source0:        https://fedorahosted.org/releases/f/a/%{name}/%{name}-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  python-setuptools
BuildRequires:  python-setuptools-devel
BuildRequires:  python-devel
BuildRequires:  python-devel
BuildRequires:  python-flask
BuildRequires:  python-fedora
BuildRequires:  python-fedora-flask
BuildRequires:  python-flask-babel
BuildRequires:  python-sqlalchemy0.7
BuildRequires:  python-flask-sqlalchemy
BuildRequires:  python-openid
Requires:       python-sqlalchemy0.7
Requires:       python-flask
Requires:       python-fedora
Requires:       python-fedora-flask
Requires:       python-flask-babel
Requires:       python-flask-sqlalchemy
Requires:       python-openid
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

%{__install} -m 644 fas_openid.conf %{buildroot}%{_sysconfdir}/httpd/conf.d/fas_openid.conf
%{__install} -d -m 644 fas_openid/static/ %{buildroot}%{_datadir}/%{name}/static
%{__install} -m 644 %{name}.cfg.sample %{buildroot}%{_sysconfdir}/%{name}/%{name}.cfg
%{__install} -m 644 %{name}.wsgi %{buildroot}%{_datadir}/%{name}/%{name}.wsgi

%pre
getent group fas-openid >/dev/null || groupadd -r fas-openid
getent passwd fas-openid >/dev/null || \
    useradd -r -g fas-openid -d %{_datadir}/%{name} -s /sbin/nologin \
    -c "Account used for FAS-OpenID serving" fas-openid
exit 0

%files
%doc
%{_sysconfdir}/%{name}
%{_sysconfdir}/httpd/conf.d/fas_openid.conf
%{_datadir}/%{name}
%{python_sitelib}/*

%changelog
* Tue Jan 29 2013 Patrick Uiterwijk <puiterwijk@gmail.com> - 0.1.1-1
- Added account creation in the RPM
- Fixed the SQLAlchemy imports to be >= 0.7
