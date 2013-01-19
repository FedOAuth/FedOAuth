#!/usr/bin/python
#-*- coding: UTF-8 -*-

## These two lines are needed to run on EL6
__requires__ = ['SQLAlchemy >= 0.7', 'jinja2 >= 2.4']
import pkg_resources

# Imports
import flask
from flask.ext.sqlalchemy import SQLAlchemy

from flask_fas import FAS

# Create the application
app = flask.Flask(__name__)
# Set up FASS
FAS = FAS(app)
app.config.from_object('fas_openid.default_config')
app.config.from_envvar('FAS_OPENID_CONFIG', silent=True)

db = SQLAlchemy(app)

import views

if __name__ == '__main__':
    app.run(debug=True)
