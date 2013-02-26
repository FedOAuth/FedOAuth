#!/usr/bin/bash -ex
if [ ! -d ".git" ];
then
    echo >&2 "Please execute utils/make_release.sh from the root"
    exit 1
fi
version=`cat fas-openid.spec | grep "Version:" | sed 's/Version:[ ]*//'`
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
if [ -f release/fas-openid-$version.tar.gz  ]
then
    echo >&2 "ERROR: release already exists. Aborted"
    exit 1
elif [ ! -z "`git tag -l v$version`"  ]
then
    echo >&2 "ERROR: release tag already exists. Aborted."
    exit 1
else
    mkdir -p release
fi
git archive --format=tar --prefix=fas-openid-$version/ HEAD | gzip > release/fas-openid-$version.tar.gz
(
    cd release
    tar zxf fas-openid-$version.tar.gz
    cd fas-openid-$version
    sed -i "s/@VERSION@/$version/" setup.py
    cp fas-openid.spec ~/rpmbuild/SPECS
    cd ..
    tar zcf fas-openid-$version.tar.gz fas-openid-$version
    gpg --detach --armor --sign fas-openid-$version.tar.gz
    scp fas-openid-$version.tar.gz{,.asc} fedorahosted.org:/srv/releases/f/a/fas-openid/
    cp fas-openid-$version.tar.gz ~/rpmbuild/SOURCES
    rm -rf fas-openid-$version
)
(
    cd ~/rpmbuild/SPECS
    rpmbuild -ba fas-openid.spec
)
cp ~/rpmbuild/SRPMS/fas-openid-$version*.src.rpm release/
ls -l release/fas-openid-$version*
echo Please build the RPM and publish it
