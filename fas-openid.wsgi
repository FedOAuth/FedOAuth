#-*- coding: UTF-8 -*-

# These two lines are needed to run on EL6
__requires__ = ['SQLAlchemy >= 0.7', 'jinja2 >= 2.4']
import pkg_resources

import os
## Set the environment variable pointing to the configuration file
os.environ['FAS_OPENID_CONFIG'] = '/etc/fas-openid/fas-openid.cfg'

## The following is only needed if you did not install
## as a python module (for example if you run it from a git clone).
#import sys
#sys.path.insert(0, '/path/to/fas_openid/')

from fas_openid import APP as application
