Summary: A pure-Python tiling window manager
Name: qtile
Version: 0.10.3
Release: 1%{?dist}
Source0: https://github.com/qtile/qtile/archive/v%{version}.tar.gz
License: MIT and GPLv3+ and ASL 2.0
# All MIT except for:
# libqtile/widget/pacman.py:GPL (v3 or later)
# libqtile/widget/google_calendar.py:Apache (v2.0)
BuildArch: noarch
Url: http://qtile.org

Source1:  qtile.desktop

BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  python3-cffi
BuildRequires:  python3-nose-cov
BuildRequires:  python3-xcffib
BuildRequires:  python3-trollius
BuildRequires:  python3-cairocffi
BuildRequires:  cairo
BuildRequires:  python3-six
BuildRequires:  python3-pycparser

Requires:  python3-cairocffi
Requires:  python3-cffi
Requires:  python3-xcffib
Requires:  python3-trollius
# python3-cairocffi is not currently pulling in cairo
Requires:  cairo

%description

A pure-Python tiling window manager.

Features
========

    * Simple, small and extensible. It's easy to write your own layouts,
      widgets and commands.
    * Configured in Python.
    * Command shell that allows all aspects of
      Qtile to be managed and inspected.
    * Complete remote scriptability - write scripts to set up workspaces,
      manipulate windows, update status bar widgets and more.
    * Qtile's remote scriptability makes it one of the most thoroughly
      unit-tested window mangers around.


%prep
%setup -q -n qtile-%{version} 

%build
%{__python3} setup.py build

%install
%{__python3} setup.py install --single-version-externally-managed -O1 --root=%{buildroot} --record=INSTALLED_FILES
mkdir -p %{buildroot}%{_datadir}/xsessions/
install -m 644 %{SOURCE1} %{buildroot}%{_datadir}/xsessions/
chmod a+x %{buildroot}%{python3_sitelib}/libqtile/confreader.py
chmod a+x %{buildroot}%{python3_sitelib}/libqtile/widget/yahoo_weather.py
chmod a+x %{buildroot}%{python3_sitelib}/libqtile/widget/bitcoin_ticker.py
chmod a+x %{buildroot}%{python3_sitelib}/libqtile/widget/sensors.py



%files
%license LICENSE
%doc README.rst
%{_mandir}/man1/qsh.1*
%{_mandir}/man1/qtile.1*
%{_bindir}/qsh
%{_bindir}/qtile
%{_bindir}/qtile-run
%{_bindir}/qtile-session
%{_bindir}/qtile-top
%{python3_sitelib}/qtile-%{version}-py%{python3_version}.egg-info
%{python3_sitelib}/libqtile
%{_datadir}/xsessions/qtile.desktop


%changelog
* Fri Dec 25 2015 John Dulaney <jdulaney@fedoraproject.org> - 0.10.3-1
- New upstream release

* Fri Nov 20 2015 John Dulaney <jdulaney@fedoraproject.org> - 0.10.2-5
- Build against new python-xcffib

* Tue Nov 10 2015 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.10.2-4
- Rebuilt for https://fedoraproject.org/wiki/Changes/python3.5

* Wed Oct 21 2015 John Dulaney <jdulaney@fedoraproject.org> - 0.10.2-3
- Fix minor issue with spec file.

* Tue Oct 20 2015 John Dulaney <jdulaney@fedoraproject.org> - 0.10.2-2
- /usr/bin/qtile-top to files list

* Tue Oct 20 2015 John Dulaney <jdulaney@fedoraproject.org> - 0.10.2-1
- Update to latest upstream

* Mon Oct 19 2015 John Dulaney <jdulaney@fedoraproject.org> - 0.10.1-1
- Fix soname issue

* Mon Aug 03 2015 John Dulaney <jdulaney@fedoraproject.org> - 0.10.1-0
- Update to latest upstream

* Mon Aug 03 2015 John Dulaney <jdulaney@fedoraproject.org> - 0.9.1-4
- Use Python3

* Thu Jun 18 2015 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.9.1-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_23_Mass_Rebuild

* Sun Feb 22 2015 John Dulaney <jdulaney@fedoraproject.org> - 0.9.1-2
- Final update to licensing

* Sat Feb 14 2015 John Dulaney <jdulaney@fedoraproject.org> - 0.9.1-1
- Update for new upstream release
- Fix license headers.

* Sun Feb 01 2015 John Dulaney <jdulaney@fedoraproject.org> - 0.9.0-2
- Update spec for qtile-0.9.0
- Include in Fedora.

* Wed Oct 08 2014 John Dulaney <jdulaney@fedoraproject.org> - 0.8.0-1
- Initial packaging
- Spec based on python-nose
