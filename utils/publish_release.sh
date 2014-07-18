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

# Check if this release already exists
if [ -z "`git tag -l v$version`"  ]
then
    echo >&2 "ERROR: release tag does not exist. Aborted."
    exit 1
fi
if [ ! -f "dist/FedOAuth-$version.tar.gz" ]
then
    echo >&2 "ERROR: release tarball does not exist. Aborted."
    exit 1
fi

# Push the git tag
git push origin "v$version"

# Upload the files
scp dist/FedOAuth-$version.tar.gz{,.asc} dist/fedoauth-$version-*.*.src.rpm puiterwijk@fedorapeople.org:public_html/FedOAuth/
echo "Release published"
