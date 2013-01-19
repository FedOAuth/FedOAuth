#-*- coding: UTF-8 -*-

import os


# url to the database server:
DB_URL = 'sqlite:////var/tmp/fas_openid_dev.sqlite'


# Path to the alembic configuration file
PATH_ALEMBIC_INI = os.path.join(os.path.dirname(os.path.abspath(__file__)),
    '..', 'alembic.ini')
