# Copyright (c) 2013, Patrick Uiterwijk <puiterwijk@gmail.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of Patrick Uiterwijk nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL Patrick Uiterwijk BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
from flaskext.babel import gettext as _

from flask import Flask, request, g, redirect, url_for, \
    abort, render_template, flash, Response
from time import time
from datetime import datetime

from fas_openid import get_session, APP as app, log_debug, \
    log_info, log_warning, log_error, get_auth_module
from fas_openid.auth.base import Auth_Base


class Auth_Test(Auth_Base):
    def logged_in(self):
        return 'loggedin' in get_session()

    def get_username(self):
        if not 'loggedin' in get_session():
            return None
        return 'tester'

    def get_sreg(self):
        if not 'loggedin' in get_session():
            return {}
        return {'username': 'tester',
                'email': 'tester@fedoauth.org',
                'fullname': 'DONT TRUST ME',
                'timezone': 'UTC'}

    def get_groups(self):
        if not 'loggedin' in get_session():
            return None
        return ['awesome']

    def check_login(self, username, password):
        if username == 'tester' and password == 'testing':
            return 'tester'
        else:
            return False

    def used_multi_factor(self):
        return False

    def used_multi_factor_physical(self):
        return False

    def used_phishing_resistant(self):
        return False

    def is_dynamic_content(self, path):
        return path.startswith('/login')

    @app.route('/login/', methods=['GET', 'POST'])
    def auth_login():
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
            if username == '' or password == '':
                user = None
            else:
                user = get_auth_module().check_login(username, password)
            if user:
                log_info('Success', {
                    'username': username,
                    'message': 'User authenticated succesfully'})
                get_session()['loggedin'] = True
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
        return render_template(
            'auth_test_login.html',
            trust_root=get_session()['trust_root'])
