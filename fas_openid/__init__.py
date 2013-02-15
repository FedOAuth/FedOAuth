#!/usr/bin/python
#-*- coding: UTF-8 -*-

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

from flask_fas import FAS

# Create the application
APP = flask.Flask(__name__)
# Set up logging (https://fedoraproject.org/wiki/Infrastructure/AppBestPractices#Centralized_logging)
logger = logging.getLogger('openid')
logger.setLevel(logging.DEBUG)
handler = logging.handlers.SysLogHandler(address='/dev/log', facility=logging.handlers.SysLogHandler.LOG_LOCAL4)
logger.addHandler(handler)
def log_create_message(message, info):
    if not 'log_id' in flask.session:
        flask.session['log_id'] = uuid().hex
    other = ''
    for key, value in info.iteritems():
        other = '%(other)s, %(key)s=%(value)s' % {'other': other, 'key': key, 'value': value}
    return '%(message)s: sessionid=%(sessionid)s %(other)s' % {'message': message, 'sessionid': flask.session['log_id'], 'other': other}

def log_info(message, info={}):
    logger.info(log_create_message(message, info))

def log_warning(message, info={}):
    logger.warning(log_create_message(message, info))

def log_error(message, info={}):
    logger.error(log_create_message(message, info))

# Set up FASS
FAS = FAS(APP)
APP.config.from_object('fas_openid.default_config')
APP.config.from_envvar('FAS_OPENID_CONFIG', silent=True)
# Set up SQLAlchemy
db = SQLAlchemy(APP)
# Set up Babel
babel = Babel(APP)

# Import the other stuff
import model
import views
