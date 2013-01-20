#-*- coding: UTF-8 -*-

import os

FAS_HTTPS_REQUIRED = False
OPENID_ENDPOINT = 'http://localhost:5000'
OPENID_IDENTITY_URL = 'http://localhost:5000/id/%s'
SECRET_KEY = 'SECRET_KEY'
DB_URL = 'sqlite:////tmp/fas_openid_dev.sqlite'
PATH_ALEMBIC_INI = os.path.join(os.path.dirname(os.path.abspath(__file__)),
    '..', 'alembic.ini')
