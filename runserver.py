#!/usr/bin/python

## These two lines are needed to run on EL6
__requires__ = ['SQLAlchemy >= 0.7', 'jinja2 >= 2.4']
import pkg_resources

from fedoauth import APP, db

# It is no problem if the database gets created every time
# as everything in it is only used during that run anyway
# (unless you want to retain sessions between restarts)
db.create_all()

APP.debug = True
APP.run()
