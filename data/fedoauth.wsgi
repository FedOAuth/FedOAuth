#-*- coding: UTF-8 -*-
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

# These two lines are needed to run on EL6
import __main__
__main__.__requires__ = ['SQLAlchemy >= 0.7', 'jinja2 >= 2.4']
import pkg_resources

import os
## Set the environment variable pointing to the configuration file
os.environ['FEDOAUTH_CONFIG'] = '/etc/fedoauth/fedoauth.cfg'

## The following is only needed if you did not install
## as a python module (for example if you run it from a git clone).
#import sys
#sys.path.insert(0, '/path/to/fedoauth/')

from fedoauth import APP as application
