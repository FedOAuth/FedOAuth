Name:           fedoauth
Version:        3.0.5
Release:        1%{?dist}
Summary:        Federated Open Authentication provider

License:        GPLv3+
URL:            https://github.com/FedOAuth/FedOAuth
Source0:        https://github.com/FedOAuth/FedOAuth/releases/download/%{version}/FedOAuth-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  python-setuptools
BuildRequires:  python-setuptools-devel
BuildRequires:  python-devel
BuildRequires:  python-flask
BuildRequires:  python-fedora
BuildRequires:  python-fedora-flask
%if 0%{?rhel} && 0%{?rhel} <= 6
BuildRequires:  python-sqlalchemy0.7
%else
BuildRequires:  python-sqlalchemy
%endif
BuildRequires:  python-flask-sqlalchemy
BuildRequires:  python-openid
BuildRequires:  python-openid-teams
BuildRequires:  python-openid-cla
BuildRequires:  m2crypto
BuildRequires:  python-enum
BuildRequires:  python-itsdangerous
%if 0%{?rhel} && 0%{?rhel} <= 6
Requires:       python-sqlalchemy0.7
%else
Requires:       python-sqlalchemy
%endif
Requires:       python-flask
Requires:       python-flask-sqlalchemy
Requires:       python-enum
Requires:       python-itsdangerous
Requires:       mod_wsgi
Requires:       httpd
Requires(pre):  shadow-utils

%description
Federated Open Authentication is an authentication provider for multiple federated authentication
systems, which can be used with any authentication backend by writing a simple module.

Currently shipped:
- OpenID
- Persona

%package template-fedoauth
Summary: General template for FedOAuth
Requires: %{name} = %{version}-%{release}
License: GPLv3+
BuildArch: noarch

%description template-fedoauth
Provides the general template files


%package template-fedora
Summary: Fedora template for FedOAuth
Requires: %{name} = %{version}-%{release}
License: GPLv3+
BuildArch: noarch

%description template-fedora
Provides the Fedora template files


%package backend-fedora
Summary: Fedora Account System authentication backend for FedOAuth
Requires: %{name} = %{version}-%{release}
License: GPLv3+
BuildArch: noarch
Requires: python-fedora
Requires: python-fedora-flask

%description backend-fedora
Provides the Fedora Account System authentication backend


%package backend-dummy
Summary: Dummy authentication backend for FedOAuth
Requires: %{name} = %{version}-%{release}
License: GPLv3+
BuildArch: noarch

%description backend-dummy
Provides the Dummy authentication backend


%package backend-webSilvia
Summary: webSilvia authentication backend for FedOAuth
Requires: %{name} = %{version}-%{release}
License: GPLv3+
BuildArch: noarch

%description backend-webSilvia
Provides the webSilvia authentication backend


%package provider-openid
Summary: OpenID provider for FedOAuth
Requires: %{name} = %{version}-%{release}
License: GPLv3+
BuildArch: noarch
Requires: python-openid
Requires: python-openid-teams
Requires: python-openid-cla

%description provider-openid
Provides the OpenID provider frontend


%package provider-persona
Summary: Persona provider for FedOAuth
Requires: %{name} = %{version}-%{release}
License: GPLv3+
BuildArch: noarch
Requires: m2crypto

%description provider-persona
Provides the Persona provider frontend


%prep
%setup -q -n FedOAuth-%{version}


%build
%{__python} setup.py build

%install
%{__python} setup.py install --skip-build --install-data=%{_datadir} --root %{buildroot}

%{__mkdir_p} %{buildroot}%{_sysconfdir}/%{name}
%{__mkdir_p} %{buildroot}%{_sysconfdir}/httpd/conf.d
%{__mkdir_p} %{buildroot}%{_datadir}/%{name}
%{__mkdir_p} %{buildroot}%{_datadir}/%{name}/static
%{__mkdir_p} %{buildroot}%{python_sitelib}/%{name}/templates
%{__mkdir_p} %{buildroot}%{_datadir}/%{name}/templates

%{__install} -m 644 data/%{name}.conf %{buildroot}%{_sysconfdir}/httpd/conf.d/%{name}.conf
%{__cp} -rp fedoauth/static/* %{buildroot}%{_datadir}/%{name}/static
%{__cp} -p fedoauth/templates/*.{html,xrds} %{buildroot}%{python_sitelib}/%{name}/templates
rm -rf fedoauth/templates/*.{html,xrds}
%{__cp} -rp fedoauth/templates/* %{buildroot}%{_datadir}/%{name}/templates
%{__install} -m 644 %{name}.cfg.sample %{buildroot}%{_sysconfdir}/%{name}/%{name}.cfg
%{__install} -m 644 createdb.py %{buildroot}%{_datadir}/%{name}/createdb.py
%{__install} -m 644 cleanup.py %{buildroot}%{_datadir}/%{name}/cleanup.py
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
%{python_sitelib}/%{name}/*.py*
%dir %{python_sitelib}/%{name}/auth
%{python_sitelib}/%{name}/auth/__init__.py*
%dir %{python_sitelib}/%{name}/provider
%{python_sitelib}/%{name}/provider/__init__.py*
%{python_sitelib}/%{name}/auth/base.py*
%{python_sitelib}/%{name}/templates/*.html
%{python_sitelib}/%{name}/templates/*.xrds
%{python_sitelib}/*.egg-info
%{_datadir}/%{name}
%dir %{_sysconfdir}/%{name}
%config(noreplace) %{_sysconfdir}/%{name}/%{name}.cfg
%{_sysconfdir}/httpd/conf.d/%{name}.conf

%files template-fedora
%{_datadir}/%{name}/static/fedora
%{_datadir}/%{name}/templates/fedora

%files template-fedoauth
%{_datadir}/%{name}/static/fedoauth
%{_datadir}/%{name}/templates/fedoauth

%files backend-fedora
%{python_sitelib}/%{name}/auth/fas.py*

%files backend-dummy
%{python_sitelib}/%{name}/auth/dummy.py*

%files backend-webSilvia
%{python_sitelib}/%{name}/auth/webSilvia.py*

%files provider-openid
%{python_sitelib}/%{name}/provider/openid.py*

%files provider-persona
%{python_sitelib}/%{name}/provider/persona.py*


%changelog
* Fry Jul 18 2014 Patrick Uiterwijk <puiterwijk@redhat.com> - 3.0.5-1
- Only give email alias with FAS module in case of CLA+1 instead of CLA [Pierre-Yves Chibon]

* Mon Jul 14 2014 Patrick Uiterwijk <puiterwijk@redhat.com> - 3.0.4-1
- Added a cleanup script to clear expired Remembered entries [Patrick Uiterwijk]

* Wed Jul 09 2014 Patrick Uiterwijk <puiterwijk@redhat.com> - 3.0.3-1
- Remove translation hooks and dependencies [Patrick Uiterwijk]
- Update webSilvia to protocol version request-1 [Patrick Uiterwijk]
- Add the FedOAuth version in the generator meta tag [Patrick Uiterwijk]
- Make it possible for the FAS module to give the users' email alias [Patrick Uiterwijk]
- Add some more logging to the transaction stealing protection [Patrick Uiterwijk]
- Make it possible to use an unlisted auth module by specifying the URL directly [Patrick Uiterwijk]

* Mon Jun 23 2014 Patrick Uiterwijk <puiterwijk@redhat.com> - 3.0.2-1
- pySilvia renamed to webSilvia [Patrick Uiterwijk]
- Auto-submit the webSilvia request form [Patrick Uiterwijk]
- Add a list of required_credentials for webSilvia [Patrick Uiterwijk]
- Only returns the intermediate API auth step if it's multi-step [Patrick Uiterwijk]
- Returns the signed OpenID response instead of an exception [Patrick Uiterwijk]

* Fri Jun 20 2014 Patrick Uiterwijk <puiterwijk@redhat.com> - 3.0.1-1
- Added pySilvia [Patrick Uiterwijk]
- Uses complete_url_for so no http -> https issues arise [Patrick Uiterwijk]
- Reworded "Remember for 0 days" to "Remember for never" [Kevin Fenzi]
- Work with newer flask.babel packages as well [Patrick Uiterwijk]

* Sun Jun 15 2014 Patrick Uiterwijk <patrick@puiterwijk.org> - 3.0.0-1
- Rewrite [Patrick Uiterwijk]

* Sat Mar 01 2014 Patrick Uiterwijk <puiterwijk@gmail.com> - 2.0.4-1
- Does not delete session when it is still valid [Patrick Uiterwijk]
- Fixes an incorrect contains [Patrick Uiterwijk]
- Now actually signs the OpenID API response [Patrick Uiterwijk]
- Send nickname with OpenID API [Patrick Uiterwijk]
- Make the remote_addr check for sessions confiruable [Patrick Uiterwijk]

* Sat Feb 15 2014 Patrick Uiterwijk <puiterwijk@gmail.com> - 2.0.3-1
- Add the magic value back for all groups

* Fri Feb 14 2014 Patrick Uiterwijk <puiterwijk@gmail.com> - 2.0.2-1
- Fixes not accepting POST for the OpenID API
- Fixes 500 when sending invalid request to OpenID API
- Make it possible to configure Persona identity issuer for delegation

* Sun Feb 09 2014 Patrick Uiterwijk <puiterwijk@gmail.com> - 2.0.1-1
- Fixes not sending the username in SReg

* Sun Feb 09 2014 Patrick Uiterwijk <puiterwijk@gmail.com> - 2.0-1
- First package after rename
- Implemented a lot of new features
