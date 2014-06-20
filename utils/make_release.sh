#!/usr/bin/bash -ex
# Copyright (C) 2014 Patrick Uiterwijk <patrick@puiterwijk.org>
#
# This file is part of FedOAuth.
#
# FedOAuth is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# FedOAuth is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with FedOAuth.  If not, see <http://www.gnu.org/licenses/>.
if [ ! -d ".git" ];
then
    echo >&2 "Please execute utils/make_release.sh from the root"
    exit 1
fi
version=`cat data/fedoauth.spec | grep "Version:" | sed 's/Version:[ ]*//'`
version_setup=`cat setup.py | grep "version=" | sed 's/[ ]*version=//' | sed "s/'//g" | sed "s/,//"`
version_news=`cat NEWS | grep Release | head -1 | sed "s/Release //" | sed "s/ (.*)//"`
if [ ! "$version" == "$version_setup" -o ! "$version" == "$version_news" ];
then
    echo "Versions do not match!"
    echo "Spec version: $version"
    echo "Setup version: $version_setup"
    echo "News version: $version_news"
    exit 1
fi
if [ -n "`git diff | head -10`" ]
then
    echo >&2 "error: tree is not clean - changes would be lost. aborted"
    exit 1
fi
if [ -n "`git log master ^origin/master`" ]
then
    echo >&2 "ERROR: unpushed changes - git push first"
    git log master ^origin/master
    exit 1
fi
if [ ! -z "`git tag -l v$version`"  ]
then
    echo >&2 "ERROR: release tag already exists. Aborted."
    exit 1
fi
git tag -s v$version -m "Release $version"
mkdir -p dist
git archive --format=tar --prefix=FedOAuth-$version/ HEAD | gzip > dist/FedOAuth-$version.tar.gz
(
    cd dist
    gpg --detach --armor --sign FedOAuth-$version.tar.gz
    cp FedOAuth-$version.tar.gz ~/rpmbuild/SOURCES
)
cp data/fedoauth.spec ~/rpmbuild/SPECS
(
    cd ~/rpmbuild/SPECS
    rpmbuild -ba fedoauth.spec
)
cp ~/rpmbuild/SRPMS/fedoauth-$version*.src.rpm dist/
ls -l dist/FedOAuth-$version* dist/fedoauth-$version*
echo Please push the tag and build and publish the RPM and sources
