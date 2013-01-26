#!/usr/bin/python
#-*- coding: UTF-8 -*-

## These two lines are needed to run on EL6
__requires__ = ['SQLAlchemy >= 0.7', 'jinja2 >= 2.4']
import pkg_resources

# Imports
import flask
from flask.ext.sqlalchemy import SQLAlchemy
from flaskext.babel import Babel

from flask_fas import FAS

# Create the application
APP = flask.Flask(__name__)
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
