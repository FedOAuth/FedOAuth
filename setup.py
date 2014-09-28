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

from setuptools import setup, find_packages

setup(name='FedOAuth',
      version='3.1.1',
      description='Federated Open Authentication provider',
      author='Patrick Uiterwijk',
      author_email='patrick@puiterwijk.org',
      url='https://github.com/FedOAuth/FedOAuth',
      license='GPLv3+',
      packages=find_packages(),
      zip_safe=False,
      include_package_data=True,
      install_requires=['Flask',
                        'SQLAlchemy>=0.7',
                        'enum', 'itsdangerous'],
      extra_require={'fas': ['python-fedora'],
                     'openid': ['python-openid',
                                'python-openid-teams',
                                'python-openid-cla'],
                     'persona': ['M2Crypto'],
                     'ldap': ['python-ldap']})
