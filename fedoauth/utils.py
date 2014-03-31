# Copyright (C) 2014 Patrick Uiterwijk <patrick@puiterwijk.org>
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
from flask import url_for, request, redirect, g
from urlparse import urljoin
from sqlalchemy.ext.mutable import Mutable
import logging

from fedoauth import APP

logger = logging.getLogger(__name__)


def complete_url_for(func, **values):
    """ Returns a full url including the url_root """
    return urljoin(APP.config['GLOBAL']['url_root'], url_for(func, **values))


def no_cache(resp):
    """ Use return no_cache(resp) to add no cache headers. """
    resp.headers['Cache-Control'] = 'no-cache, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = 'Sat, 26 Jul 1997 05:00:00 GMT'
    return resp


class _NotLoggedinError(Exception):
    """ Internal """
    pass


@APP.errorhandler(_NotLoggedinError)
def _handle_notloggedin(_):
    """ Internal """
    return redirect(url_for('view_authenticate',
                            transaction=request.transaction_id))


def require_login(login_target,
                  view_success,
                  view_failure,
                  username=None,
                  email_auth_domain=None,
                  requested_attributes=[]):
    """ Function that verifies the user is authenticated.
        login_target is the string to display to the user.
        view_success is most often the calling function.
        view_failure is the function the user will be redirected to in case of
        authentication cancellation."""
    if not request.auth_module:
        request.transaction['login_target'] = login_target
        request.transaction['success_forward'] = view_success
        request.transaction['failure_forward'] = view_failure
        if username is not None:
            request.transaction['forced_username'] = username
        if email_auth_domain is not None:
            request.transaction['email_auth_domain'] = email_auth_domain
        request.transaction['requested_attributes'] = requested_attributes
        request.save_transaction()
        raise _NotLoggedinError()


def after_this_request(func):
    """ Add this decorator to execute a function at the end of the current
        request.
        Source: http://flask.pocoo.org/snippets/53/"""
    if not hasattr(g, 'call_after_request'):
        g.call_after_request = []
    logger.debug('Calling %s after request', func.func_name)
    g.call_after_request.append(func)
    return func


@APP.after_request
def _per_request_callbacks(response):
    """ Internal """
    for func in getattr(g, 'call_after_request', ()):
        logger.debug('Calling %s', func.func_name)
        new_response = func(response)
        if new_response is not None:
            response = new_response
    return response


class BackportedMutableDict(Mutable, dict):
    """ The exact same code as the official MutableDict in version 0.9.
        Backported because it was introduces in 0.8, and EPEL includes 0.7"""
    def __setitem__(self, key, value):
        """Detect dictionary set events and emit change events."""
        dict.__setitem__(self, key, value)
        self.changed()

    def __delitem__(self, key):
        """Detect dictionary del events and emit change events."""
        dict.__delitem__(self, key)
        self.changed()

    def clear(self):
        dict.clear(self)
        self.changed()

    @classmethod
    def coerce(cls, key, value):
        """Convert plain dictionary to MutableDict."""
        if not isinstance(value, BackportedMutableDict):
            if isinstance(value, dict):
                return BackportedMutableDict(value)
            return Mutable.coerce(key, value)
        else:
            return value

    def __getstate__(self):
        return dict(self)

    def __setstate__(self, state):
        self.update(state)


# SOURCE: http://flask.pocoo.org/snippets/35/
class ReverseProxied(object):
    '''Wrap the application in this middleware and configure the
front-end server to add these headers, to let you quietly bind
this to a URL other than / and to an HTTP scheme that is
different than what is used locally.

In nginx:
location /myprefix {
proxy_pass http://192.168.0.1:5001;
proxy_set_header Host $host;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Scheme $scheme;
proxy_set_header X-Script-Name /myprefix;
}

:param app: the WSGI application
'''
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = environ.get('HTTP_X_SCRIPT_NAME', '')
        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]

        server = environ.get('HTTP_X_FORWARDED_HOST', '')
        if server:
            environ['HTTP_HOST'] = server

        scheme = environ.get('HTTP_X_SCHEME', '')
        if scheme:
            environ['wsgi.url_scheme'] = scheme
        return self.app(environ, start_response)
