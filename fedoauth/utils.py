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
from urlparse import urljoin

from fedoauth import APP as app, get_session
from flask import Flask, request, g, redirect, url_for


def complete_url_for(func, **values):
    return urljoin(app.config['WEBSITE_ROOT'], url_for(func, **values))


def addToSessionArray(array, value):
    if array in get_session():
        get_session()[array].append(value)
        get_session().save()
    else:
        get_session()[array] = [value]
        get_session().save()


def getSessionValue(key, default_value=None):
    if key in get_session():
        return get_session()[key]
    else:
        return default_value


def no_cache(resp):
    resp.headers['Cache-Control'] = 'no-cache, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = 'Sat, 26 Jul 1997 05:00:00 GMT'
    return resp


