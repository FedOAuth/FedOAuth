from time import time
from datetime import datetime
import sys
from urlparse import urljoin
from uuid import uuid4 as uuid

from flask import Flask, request, g, redirect, url_for, \
    abort, render_template, flash, Response
from flaskext.babel import gettext as _

from model import FASOpenIDStore
from fas_openid import APP as app, get_session, log_debug, \
    log_info, log_warning, log_error, get_auth_module


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


@app.route('/robots.txt')
def view_robots():
    return 'User-Agent: *\nDisallow: /'


@app.route('/', methods=['GET', 'POST'])
def view_main():
    return render_template(
        'index.html',
        yadis_url=complete_url_for('view_yadis')
    ), 200, {'X-XRDS-Location': complete_url_for('view_yadis')}


@app.route('/logout/')
def auth_logout():
    # No check if we are logged in, as we can always delete the session
    get_session().delete()
    flash(_('You have been logged out'))
    return redirect(url_for('view_main'))
