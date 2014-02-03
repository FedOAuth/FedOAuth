#!/usr/bin/bash -ex
if [ ! -d ".git" ];
then
    echo >&2 "Please execute utils/make_release.sh from the root"
    exit 1
fi
version=`cat fedoauth.spec | grep "Version:" | sed 's/Version:[ ]*//'`
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
if [ -f release/fedoauth-$version.tar.gz  ]
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
git branch make-release
git checkout make-release
tx pull -a
git add fedoauth/translations
git commit -m "Updated translations"
git tag -s v$version -m "Release v$version"
git checkout master
git branch -D make-release
git push origin v$version
git archive --format=tar --prefix=fedoauth-$version/ HEAD | gzip > release/fedoauth-$version.tar.gz
(
    cd release
    tar zxf fedoauth-$version.tar.gz
    cd fedoauth-$version
    sed -i "s/@VERSION@/$version/" setup.py
    cp fedoauth.spec ~/rpmbuild/SPECS
    cd ..
    tar zcf fedoauth-$version.tar.gz fedoauth-$version
    gpg --detach --armor --sign fedoauth-$version.tar.gz
    scp fedoauth-$version.tar.gz{,.asc} fedorahosted.org:/srv/web/releases/f/a/fedoauth/
    cp fedoauth-$version.tar.gz ~/rpmbuild/SOURCES
    rm -rf fedoauth-$version
)
(
    cd ~/rpmbuild/SPECS
    rpmbuild -ba fedoauth.spec >/dev/null
)
cp ~/rpmbuild/SRPMS/fedoauth-$version*.src.rpm release/
ls -l release/fedoauth-$version*
echo Please build the RPM and publish it
