#-*- coding: UTF-8 -*-

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
