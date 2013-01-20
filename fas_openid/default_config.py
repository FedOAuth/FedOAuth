#-*- coding: UTF-8 -*-

import os

FAS_HTTPS_REQUIRED = False

SECRET_KEY = 'SECRET_KEY'
# url to the database server:
DB_URL = 'sqlite:////tmp/fas_openid_dev.sqlite'


# Path to the alembic configuration file
PATH_ALEMBIC_INI = os.path.join(os.path.dirname(os.path.abspath(__file__)),
    '..', 'alembic.ini')
