#!/usr/bin/python
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

## These two lines are needed to run on EL6
__requires__ = ['SQLAlchemy >= 0.7', 'jinja2 >= 2.4']
import pkg_resources

# Imports
import flask
import jinja2

import logging
import logging.config

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

import sys


# Create the application
APP = flask.Flask(__name__)


APP.config.from_envvar('FEDOAUTH_CONFIG')

# Make sure the configuration is sane
if APP.config['GLOBAL']['url_root'].endswith('/'):
    print 'Error: Make sure url_root does NOT end with a trailing slash'
    sys.exit(1)
if APP.config['GLOBAL']['secret_key'] == 'setme':
    print 'Error: Please configure a secret key'
    sys.exit(1)

logging.config.fileConfig(APP.config['GLOBAL']['logging_config_location'])


logger = logging.getLogger(__name__)


# Set up SQLAlchemy
# DEPRECATED: the global SQLALCHEMY_DATABASE_URI is deprecated, but should stay supported during the 3.0.X series
db_url = None
db_debug = APP.config['GLOBAL'].get('database_debug', False)
if 'database_url' in APP.config['GLOBAL']:
    db_url = APP.config['GLOBAL']['database_url']
else:
    db_url = APP.config['SQLALCHEMY_DATABASE_URI']
dbengine = create_engine(db_url, echo=db_debug, pool_recycle=3600)
dbsession = scoped_session(sessionmaker(bind=dbengine))

from fedoauth.utils import ReverseProxied
if APP.config['GLOBAL']['reverse_proxied']:
    APP.wsgi_app = ReverseProxied(APP.wsgi_app)


# Transaction stuff
# Please prefix module-specific keys with __name__ to prevent key collisions
from fedoauth.lib.transaction import TransactionRequest
APP.request_class = TransactionRequest

# Use the templates
# First we test the core templates directory
#  (contains stuff that users won't see)
# Then we use the configured template directory
templ_loaders = []
templ_loaders.append(APP.jinja_loader)
templ_loaders.append(jinja2.FileSystemLoader('%s' % APP.config['GLOBAL']['template_dir']))
templ_loaders.append(jinja2.FileSystemLoader('%s' % APP.config['GLOBAL']['global_template_dir']))

APP.jinja_loader = jinja2.ChoiceLoader(templ_loaders)

APP.jinja_env.globals['url_root'] = APP.config['GLOBAL']['url_root']
APP.jinja_env.globals['static_content_root'] = APP.config['GLOBAL']['static_content_root']
try:
    APP.jinja_env.globals['version'] = pkg_resources.get_distribution('fedoauth').version
except:
    APP.jinja_env.globals['version'] = 'Unknown. Development?'


app_version = 'Development version'
try:
    app_version = pkg_resources.get_distribution("fedoauth").version
except:
    pass
APP.jinja_env.globals['VERSION'] = app_version


# Import the other stuff (this needs to be done AFTER setting db connection)
# Import enabled auth methods
loaded_auth_modules = []


def get_auth_module_by_name(name):
    global loaded_auth_modules
    for loaded_auth_module in loaded_auth_modules:
        if name == loaded_auth_module._internal_name:
            return loaded_auth_module


def get_loaded_auth_modules():
    global loaded_auth_modules
    return loaded_auth_modules


# Initialize all the enabled auth modules
for auth_module_name in APP.config['AUTH_MODULE_CONFIGURATION']:
    if APP.config['AUTH_MODULE_CONFIGURATION'][auth_module_name]['enabled']:
        auth_module_name_split = auth_module_name.rsplit('.', 1)
        # This fromlist= is because otherwise it will only import the module
        auth_module = __import__(auth_module_name_split[0],
                                 fromlist=[auth_module_name_split[1]])
        auth_module = getattr(auth_module, auth_module_name_split[1])
        auth_module = auth_module(APP.config['AUTH_MODULE_CONFIGURATION'][auth_module_name])
        auth_module._internal_name = auth_module_name
        loaded_auth_modules.append(auth_module)


import views

for provider in APP.config['AUTH_PROVIDER_CONFIGURATION']:
    if APP.config['AUTH_PROVIDER_CONFIGURATION'][provider]['enabled']:
        provider_module = __import__(provider)
