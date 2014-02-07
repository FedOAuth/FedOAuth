Name:           fedoauth
Version:        2.0
Release:        1%{?dist}
Summary:        Federated Open Authentication provider

License:        GPLv3+
URL:            https://github.com/fedora-infra/%{name}
Source0:        https://fedorahosted.org/releases/f/a/%{name}/%{name}-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  python-setuptools
BuildRequires:  python-setuptools-devel
BuildRequires:  python-devel
BuildRequires:  python-flask
BuildRequires:  python-fedora
BuildRequires:  python-fedora-flask
BuildRequires:  python-flask-babel <= 0.8
BuildRequires:  python-sqlalchemy0.7
BuildRequires:  python-flask-sqlalchemy
BuildRequires:  python-openid
BuildRequires:  python-openid-teams
BuildRequires:  python-openid-cla
Requires:       python-sqlalchemy0.7
Requires:       python-flask
Requires:       python-fedora
Requires:       python-fedora-flask
Requires:       python-flask-babel <= 0.8
Requires:       python-flask-sqlalchemy
Requires:       python-openid
Requires:       python-openid-teams
Requires:       python-openid-cla
Requires:       mod_wsgi
Requires:       httpd
Requires(pre):  shadow-utils

%description
Federated Open Authentication is an authentication provider for multiple federated authentication
systems, which can be used with any authentication backend by writing a simple module.

Currently implemented:
- OpenID
- Persona

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

%{__install} -m 644 %{name}.conf %{buildroot}%{_sysconfdir}/httpd/conf.d/%{name}.conf
%{__install} -m 644 fedoauth/static/* %{buildroot}%{_datadir}/%{name}/static
%{__install} -m 644 %{name}.cfg.sample %{buildroot}%{_sysconfdir}/%{name}/%{name}.cfg
%{__install} -m 644 createdb.py %{buildroot}%{_datadir}/%{name}/createdb.py
%{__install} -m 644 %{name}.wsgi %{buildroot}%{_datadir}/%{name}/%{name}.wsgi

%pre
getent group fedoauth >/dev/null || groupadd -r fedoauth
getent passwd fedoauth >/dev/null || \
    useradd -r -g fedoauth -d %{_datadir}/%{name} -s /sbin/nologin \
    -c "Account used for FedOAuth serving" fedoauth
exit 0

%files
%doc AUTHORS COPYING README
%dir %{_sysconfdir}/%{name}
%config(noreplace) %{_sysconfdir}/%{name}/%{name}.cfg
%config(noreplace) %{_sysconfdir}/httpd/conf.d/%{name}.conf
%{_datadir}/%{name}
%{python_sitelib}/*

%changelog
* Mon Feb 03 2014 Patrick Uiterwijk <puiterwijk@gmail.com> - 2.0-1
- First package after rename
