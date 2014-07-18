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
#
# Check for sanity of the call
if [ ! -d ".git" ];
then
    echo >&2 "Please execute utils/make_release.sh from the root"
    exit 1
fi

# Check for sanity of the versions
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

# Check for any non-committed or non-pushed changes
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

# Check if this release already exists
if [ ! -z "`git tag -l v$version`"  ]
then
    echo >&2 "ERROR: release tag already exists. Aborted."
    exit 1
fi

# Do some smoketests here
python -m py_compile `find -name "*.py"`

# Create the destination directory if it does not yet exist
mkdir -p dist

# Archive the build
git archive --format=tar --prefix=FedOAuth-$version/ HEAD | gzip > dist/FedOAuth-$version.tar.gz

# Build (S)RPM as smoketest The produced RPM is not meant for redistribution
mock --resultdir=./dist/ --buildsrpm --spec data/fedoauth.spec --sources dist/ -r fedora-rawhide-x86_64
mock --rebuild dist/fedoauth-$version-*.*.src.rpm -r fedora-rawhide-x86_64

# Tag the actual release
git tag -s v$version -m "Release $version"

# Sign the release
gpg --detach --armor --sign dist/FedOAuth-$version.tar.gz

# Echo the files to upload
ls -l dist/FedOAuth-$version* dist/fedoauth-$version*
echo Please push the tag and build and publish the RPM and sources
