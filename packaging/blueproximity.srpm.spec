# https://fedoraproject.org/wiki/How_to_create_an_RPM_package
# Built and maintained by John Boero - boeroboy@gmail.com
# In honor of Seth Vidal https://www.redhat.com/it/blog/thank-you-seth-vidal

Name:           blueproximity
Version:        1.4.0
Release:        1%{?dist}
Summary:        This software helps you add a little more security to your desktop. It does so by detecting one of your bluetooth devices, most likely your mobile phone, and keeping track of its distance.
License:        GPLv2
Source0:	    https://github.com/jboero/blueproximity/archive/refs/tags/v%{version}.tar.gz
BuildRequires:  coreutils desktop-file-utils
Requires:	    desktop-file-utils bluez-deprecated python3-bluez python3-configobj python3-xapp
URL:            https://github.com/tiktaalik-dev/blueproximity

%define debug_package %{nil}
%define source_date_epoch_from_changelog 0

%description
Original by Lars Friedrichs and Rodrigo Gambra-Middleton (rodrigo@tiktaalik.dev)

If you move away from your computer and the distance is above a certain level for a given time, it automatically locks your desktop (or starts any other shell command you want).

Once away your computer awaits its master back - if you are nearer than a given level for a set time your computer unlocks magically without any interaction (or starts any other shell command you want).

See the doc/ directory or the website which both contain a manual with screenshots.

Note beware Bluetooth MAC spoofing. This will only work with paired devices for security. Does not support BTLE.
%prep
%autosetup -n blueproximity-packaging

%build

%install
pwd
mkdir -p %{buildroot}%{_datadir}/{%{name},pixmaps} %{buildroot}%{_bindir}
cp -p *.py *.svg *.glade %{buildroot}%{_datadir}/%{name}/
cp addons/blueproximity %{buildroot}%{_bindir}
cp addons/blueproximity.xpm %{buildroot}%{_datadir}/pixmaps/

desktop-file-install addons/blueproximity.desktop

%clean
rm -rf %{buildroot}
rm -rf %{_builddir}/*

%files
%{_bindir}/%{name}
%{_datadir}/%{name}/*
%{_datadir}/applications/%{name}.desktop
%{_datadir}/pixmaps/%{name}.xpm
%pre

%post

%preun
%postun

%changelog
