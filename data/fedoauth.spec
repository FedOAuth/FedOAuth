Name:           fedoauth
Version:        2.0.2
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
%if 0%{?rhel}
BuildRequires:  python-sqlalchemy0.7
%else
BuildRequires:  python-sqlalchemy
%endif
BuildRequires:  python-flask-sqlalchemy
BuildRequires:  python-openid
BuildRequires:  python-openid-teams
BuildRequires:  python-openid-cla
BuildRequires:  m2crypto
%if 0%{?rhel}
Requires:       python-sqlalchemy0.7
%else
Requires:       python-sqlalchemy
%endif
Requires:       python-flask
Requires:       python-fedora
Requires:       python-fedora-flask
Requires:       python-flask-babel <= 0.8
Requires:       python-flask-sqlalchemy
Requires:       python-openid
Requires:       python-openid-teams
Requires:       python-openid-cla
Requires:       m2crypto
Requires:       mod_wsgi
Requires:       httpd
Requires(pre):  shadow-utils

%description
Federated Open Authentication is an authentication provider for multiple federated authentication
systems, which can be used with any authentication backend by writing a simple module.

Currently implemented:
- OpenID
- Persona

%package template-fedora
Summary: Provides the Fedora template files
Requires: %{name} = %{version}-%{release}
License: GPLv3+
BuildArch: noarch

%description template-fedora
Provides the Fedora template files

%package backend-fedora
Summary: Provides the Fedora authentication backend
Requires: %{name} = %{version}-%{release}
License: GPLv3+
BuildArch: noarch

%description backend-fedora
Provides the Fedora authentication backend


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

%{__install} -m 644 data/%{name}.conf %{buildroot}%{_sysconfdir}/httpd/conf.d/%{name}.conf
%{__install} -m 644 fedoauth/static/* %{buildroot}%{_datadir}/%{name}/static
%{__install} -m 644 %{name}.cfg.sample %{buildroot}%{_sysconfdir}/%{name}/%{name}.cfg
%{__install} -m 644 createdb.py %{buildroot}%{_datadir}/%{name}/createdb.py
%{__install} -m 644 data/%{name}.wsgi %{buildroot}%{_datadir}/%{name}/%{name}.wsgi

rm -f %{buildroot}%{_datadir}/%{name}/static/logo.svg

%pre
getent group fedoauth >/dev/null || groupadd -r fedoauth
getent passwd fedoauth >/dev/null || \
    useradd -r -g fedoauth -d %{_datadir}/%{name} -s /sbin/nologin \
    -c "Account used for FedOAuth serving" fedoauth
exit 0

%files
%doc AUTHORS COPYING README NEWS
%dir %{python_sitelib}/%{name}
%{python_sitelib}/%{name}/__init__.py*
%{python_sitelib}/%{name}/model.py*
%{python_sitelib}/%{name}/proxied.py*
%{python_sitelib}/%{name}/utils.py*
%{python_sitelib}/%{name}/views.py*
%{python_sitelib}/%{name}/views_openid.py*
%{python_sitelib}/%{name}/views_persona.py*
%{python_sitelib}/%{name}/translations
%{python_sitelib}/%{name}/auth/__init__.py*
%{python_sitelib}/%{name}/auth/base.py*
%{python_sitelib}/%{name}/templates/openid_user.html
%{python_sitelib}/%{name}/templates/openid_yadis.xrds
%{python_sitelib}/%{name}/templates/openid_yadis_user.xrds
%{python_sitelib}/%{name}/templates/persona_provision.html
%{python_sitelib}/%{name}/templates/persona_signin.html
%{python_sitelib}/*.egg-info
%{_datadir}/%{name}
%dir %{_sysconfdir}/%{name}
%{_sysconfdir}/%{name}/%{name}.cfg
%{_sysconfdir}/httpd/conf.d/%{name}.conf


%files template-fedora
%{_datadir}/%{name}/static/fedora-authn-logo-white.png
%{_datadir}/%{name}/static/fedora.css
%{_datadir}/%{name}/static/repeater.png
%{python_sitelib}/%{name}/templates/index.html
%{python_sitelib}/%{name}/templates/layout.html
%{python_sitelib}/%{name}/templates/openid_user_ask_trust_root.html

%files backend-fedora
%{python_sitelib}/%{name}/auth/fas.py*
%{python_sitelib}/%{name}/templates/auth_fas_login.html


%changelog
* Fri Feb 14 2014 Patrick Uiterwijk <puiterwijk@gmail.com> - 2.0.2-1
- Fixes not accepting POST for the OpenID API
- Fixes 500 when sending invalid request to OpenID API
- Make it possible to configure Persona identity issuer for delegation

* Sun Feb 09 2014 Patrick Uiterwijk <puiterwijk@gmail.com> - 2.0.1-1
- Fixes not sending the username in SReg

* Sun Feb 09 2014 Patrick Uiterwijk <puiterwijk@gmail.com> - 2.0-1
- First package after rename
- Implemented a lot of new features
