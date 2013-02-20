#!/usr/bin/python
#-*- coding: UTF-8 -*-

## These two lines are needed to run on EL6
__requires__ = ['SQLAlchemy >= 0.7', 'jinja2 >= 2.4']
import pkg_resources

# Imports
import flask
from beaker.middleware import SessionMiddleware
from flask.ext.sqlalchemy import SQLAlchemy
from flaskext.babel import Babel

import logging
import logging.handlers

from uuid import uuid4 as uuid
import sys

# Create the application
APP = flask.Flask(__name__)
# Set up logging (https://fedoraproject.org/wiki/Infrastructure/AppBestPractices#Centralized_logging)
FORMAT = '%(asctime)-15s OpenID[%(process)d] %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger('openid')
logger.setLevel(logging.DEBUG)
handler = logging.handlers.SysLogHandler(address='/dev/log', facility=logging.handlers.SysLogHandler.LOG_LOCAL4)
logger.addHandler(handler)
def log_create_message(message, info):
    if not 'log_id' in get_session():
        get_session()['log_id'] = uuid().hex
        get_session().save()
    other = ''
    for key, value in info.iteritems():
        other = '%(other)s, %(key)s=%(value)s' % {'other': other, 'key': key, 'value': value}
    return '%(message)s: sessionid=%(sessionid)s%(other)s' % {'message': message, 'sessionid': get_session()['log_id'], 'other': other}

def log_debug(message, info={}):
    logger.debug(log_create_message(message, info))

def log_info(message, info={}):
    logger.info(log_create_message(message, info))

def log_warning(message, info={}):
    logger.warning(log_create_message(message, info))

def log_error(message, info={}):
    logger.error(log_create_message(message, info))

def get_session():
    return flask.request.environ['beaker.session']

APP.config.from_object('fas_openid.default_config')
APP.config.from_envvar('FAS_OPENID_CONFIG', silent=True)

if not APP.config['SQLALCHEMY_DATABASE_URI'] or APP.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite'):
    print 'Error: FAS-OpenID cannot work with sqlite, please configure a real database'
    sys.exit(1)

# Set up SQLAlchemy
db = SQLAlchemy(APP)
# Set up Babel
babel = Babel(APP)
# Set up sessions
session_opts = {
    'session.lock_dir': '/tmp/beaker',
    'session.type': 'ext:database',
    'session.url': APP.config['SQLALCHEMY_DATABASE_URI'],
    'session.auto': False,
    'session.cookie_expires': True,
    'session.key': 'FAS_OPENID',
    'session.secret': APP.config['SECRET_KEY'],
    'session.secure': False
}
APP.wsgi_app = SessionMiddleware(APP.wsgi_app, session_opts)

# Import the other stuff
import model
import views
