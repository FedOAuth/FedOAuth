# Copyright (C) 2014 Patrick Uiterwijk <puiterwijk@gmail.com>
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

## These two lines are needed to run on EL6
__requires__ = ['SQLAlchemy >= 0.7', 'jinja2 >= 2.4']
import pkg_resources


from setuptools import setup, find_packages

setup(name='FedOAuth',
      version='@VERSION@',
      author='Patrick Uiterwijk',
      author_email='puiterwijk@gmail.com',
      packages=find_packages(),
      zip_safe=False,
      include_package_data=True,
      install_requires=['Flask', 'SQLAlchemy>=0.7',
                        'python-openid', 'flask-sqlalchemy',
                        'flask-babel',
                        'python-openid-teams',
                        'python-openid-cla'])
