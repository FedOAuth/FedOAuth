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
try:
    from flask import _app_ctx_stack as stack
except ImportError:
    from flask import _request_ctx_stack as stack
from flaskext.babel import gettext as _

from flask import Flask, request, g, redirect, url_for, \
    abort, render_template, flash, Response
from time import time
from datetime import datetime
import urllib

from fedora.client.fasproxy import FasProxyClient
from fedora.client import AuthError

from fedoauth import get_session, APP as app, log_debug, \
    log_info, log_warning, log_error, get_auth_module
from fedoauth.auth.base import Auth_Base
from fedoauth.utils import complete_url_for


class Auth_FAS(Auth_Base):
    def _get_fasclient(self):
        ctx = stack.top
        if not hasattr(ctx, 'fasclient'):
            ctx.fasclient = FasProxyClient(
                base_url=app.config['FAS_BASE_URL'],
                useragent=app.config['FAS_USER_AGENT'],
                insecure=not app.config['FAS_CHECK_CERT'])
        return ctx.fasclient

    def logged_in(self):
        return 'user' in get_session()

    def start_authentication(self):
        return redirect(complete_url_for('view_fas_login'))

    def get_persona_auth_base(self):
        return "auth_fas_login.html"

    def get_username(self):
        if not 'user' in get_session():
            return None
        return get_session()['user']['username']

    def get_sreg(self):
        if not 'user' in get_session():
            return {}
        return {'nickname': self.get_username(),
                'email': get_session()['user']['email'],
                'fullname': get_session()['user']['human_name'],
                'timezone': get_session()['user']['timezone']}

    def get_groups(self):
        if not 'user' in get_session():
            return None
        return get_session()['user']['groups']

    def check_login(self, username, password):
        try:
            session_id, data = self._get_fasclient().login(username, password)
            return data.user
        except AuthError:
            return False
        except Exception, ex:
            log_warning('Error', {
                'message': 'An error occured while checking username/password: %s'
                % ex})
            return False

    def api_authenticate(self, post_data):
        if not 'username' in post_data or not 'password' in post_data:
            return False
        username = post_data['username']
        password = post_data['password']
        if not username or not password:
            return False
        user = get_auth_module().check_login(username, password)
        if not user:
            return False
        user['groups'] = [x['name'] for x in user['approved_memberships']]
        user['last_auth_time'] = time()
        return { 'username': user['username']
               , 'email': user['email']
               , 'fullname': user['human_name']
               , 'timezone': user['timezone']
               , 'groups': user['groups']
               }

    def used_multi_factor(self):
        return False

    def used_multi_factor_physical(self):
        return False

    def used_phishing_resistant(self):
        return False

    @app.route('/fas/login/persona/', methods=['POST'])
    def view_persona_fas_login():
        if not 'username' in request.form or not 'password' in  request.form:
            return Response('No user or pw', status=400)
        if get_auth_module().logged_in():
            return Response('Already logged in', status=409)
        username = request.form['username']
        password = request.form['password']
        if (not app.config['FAS_AVAILABLE_FILTER']) or \
                (username in app.config['FAS_AVAILABLE_TO']):
            if username == '' or password == '':
                user = None
            else:
                user = get_auth_module().check_login(username, password)
            if user:
                log_info('Success', {
                    'username': username,
                    'message': 'User authenticated succesfully'})
                user = user.toDict()  # A bunch is not serializable...
                user['groups'] = [x['name'] for x in
                                  user['approved_memberships']]
                get_session()['user'] = user
                get_session()['last_auth_time'] = time()
                get_session()['timeout'] = False
                get_session()['trust_root'] = ''
                get_session().save()
                return Response('Success', status=200)
            else:
                log_warning('Failure', {
                    'username': username,
                    'message': 'User entered incorrect username or password'})
                return Response('Incorrect username or password', status=403)
        else:
            log_warning('Failure', {
                'username': username,
                'message': 'Tried to login with an account that is not '
                           'allowed to use this service'})
            return Response('Service limited to a restricted set of users', status=403)


    @app.route('/fas/login/', methods=['GET', 'POST'])
    def view_fas_login():
        if not 'next' in request.args and not 'next' in get_session():
            return redirect(url_for('view_main'))
        if 'next' in request.args:
            get_session()['next'] = request.args['next']
            get_session().save()
        if get_auth_module().logged_in() and not \
                ('timeout' in get_session() and get_session()['timeout']):
            # We can also have "timeout" as of 0.4.0
            # indicating PAPE or application configuration requires a re-auth
            log_debug('Info', {
                'message': 'User tried to login but is already authenticated'})
            return redirect(get_session()['next'])
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            if (not app.config['FAS_AVAILABLE_FILTER']) or \
                    (username in app.config['FAS_AVAILABLE_TO']):
                if username == '' or password == '':
                    user = None
                else:
                    user = get_auth_module().check_login(username, password)
                if user:
                    log_info('Success', {
                        'username': username,
                        'message': 'User authenticated succesfully'})
                    user = user.toDict()  # A bunch is not serializable...
                    user['groups'] = [x['name'] for x in
                                      user['approved_memberships']]
                    get_session()['user'] = user
                    get_session()['last_auth_time'] = time()
                    get_session()['timeout'] = False
                    get_session()['trust_root'] = ''
                    get_session().save()
                    return redirect(get_session()['next'])
                else:
                    log_warning('Failure', {
                        'username': username,
                        'message': 'User entered incorrect username or password'})
                    flash(_('Incorrect username or password'))
            else:
                log_warning('Failure', {
                    'username': username,
                    'message': 'Tried to login with an account that is not '
                               'allowed to use this service'})
                flash(_('This service is limited to the following '
                        'users: %(users)s',
                        users=', '.join(app.config['FAS_AVAILABLE_TO'])))
        return render_template(
            'auth_fas_login.html',
            trust_root=get_session()['trust_root'])
