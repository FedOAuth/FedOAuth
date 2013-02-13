#-*- coding: UTF-8 -*-

import os

AVAILABLE_FILTER = False
AVAILABLE_TO = []

TRUSTED_ROOTS = []
NON_TRUSTED_ROOTS = []

MAX_AUTH_TIME = 15

LOGIN_URL = 'http://localhost:5000/login/'

FAS_HTTPS_REQUIRED = True
OPENID_ENDPOINT = 'http://localhost:5000'
OPENID_IDENTITY_URL = 'http://localhost:5000/id/%s/'
SECRET_KEY = 'SECRET_KEY'
SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/fas_openid_dev.sqlite'
