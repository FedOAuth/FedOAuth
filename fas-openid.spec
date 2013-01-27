Name:           fas-openid
Version:        0.1.0
Release:        1%{?dist}
Summary:        An OpenID provider which authenticates users against FAS

License:        GPLv2+
URL:            https://github.com/fedora-infra/%{name}
Source0:        https://github.com/fedora-infra/%{name}/archive/v%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  python-setuptools
BuildRequires:  python-setuptools-devel
BuildRequires:  python-devel
BuildRequires:  python-devel
BuildRequires:  python-flask
BuildRequires:  python-fedora
BuildRequires:  python-fedora-flask
BuildRequires:  python-flask-sqlalchemy
BuildRequires:  python-openid
Requires:       python-flask
Requires:       python-fedora
Requires:       python-fedora-flask
Requires:       python-flask-sqlalchemy
Requires:       python-openid
Requires:       mod_wsgi
Requires:       httpd

%description
FAS-OpenID is an OpenID provider which gets it's information from Fedora Account System (FAS).

%prep
%setup -q


%build
%{__python} setup.py build --install-data=%{_datadir}

%install
%{__python} setup.py install --skip-build --install-data=%{_datadir} --root %{buildroot}

%{__mkdir_p} %{buildroot}/var/lib/fas-openid
%{__mkdir_p} %{buildroot}%{_sysconfdir}/httpd/conf.d
%{__mk

%files
%doc



%changelog
