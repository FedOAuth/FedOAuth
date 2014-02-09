#!/usr/bin/python
#-*- coding: UTF-8 -*-
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

# Imports
import flask
from flask.ext.sqlalchemy import SQLAlchemy
from flaskext.babel import Babel

import logging
import logging.handlers

from uuid import uuid4 as uuid
import sys

from proxied import ReverseProxied

# Create the application
APP = flask.Flask(__name__)
# Set up logging
# (https://fedoraproject.org/wiki/Infrastructure/AppBestPractices)
FORMAT = '%(asctime)-15s OpenID[%(process)d] %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger('openid')
logger.setLevel(logging.DEBUG)
handler = logging.handlers.SysLogHandler(
    address='/dev/log',
    facility=logging.handlers.SysLogHandler.LOG_LOCAL4)
logger.addHandler(handler)


def log_create_message(message, info):
    if not 'log_id' in get_session():
        get_session()['log_id'] = uuid().hex
        get_session().save()
    other = ''
    for key, value in info.iteritems():
        other = '%(other)s, %(key)s=%(value)s' % {
            'other': other,
            'key': key,
            'value': value}
    return '%(message)s: sessionid=%(sessionid)s%(other)s' % {
        'message': message,
        'sessionid': get_session()['log_id'],
        'other': other}


def log_debug(message, info={}):
    logger.debug(log_create_message(message, info))


def log_info(message, info={}):
    logger.info(log_create_message(message, info))


def log_warning(message, info={}):
    logger.warning(log_create_message(message, info))


def log_error(message, info={}):
    logger.error(log_create_message(message, info))


def get_session():
    return flask.session


APP.config.from_envvar('FEDOAUTH_CONFIG')

# Make sure the configuration is sane
if not APP.config['SQLALCHEMY_DATABASE_URI']:
    print 'Error: Please make sure to configure SQLALCHEMY_DATABASE_URI'
    sys.exit(1)
if APP.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres:'):
    print 'Error: Please use the postgresql dialect (postgresql: '\
        'instead of postgres: in the database URI)'
    sys.exit(1)

# Set up SQLAlchemy
db = SQLAlchemy(APP)
# Set up Babel
babel = Babel(APP)
APP.wsgi_app = ReverseProxied(APP.wsgi_app)

# Import the other stuff (this needs to be done AFTER setting db connection)
# Import enabled auth method
def get_auth_module():
    global auth_module
    return auth_module
auth_module_name = APP.config['AUTH_MODULE'].rsplit('.', 1)
auth_module = __import__(auth_module_name[0], fromlist=[auth_module_name[1]])
auth_module = getattr(auth_module, auth_module_name[1])
auth_module = auth_module(APP.config)


import model
import views
import views_openid
import views_persona

APP.session_interface = model.DBSessionMiddleware()
