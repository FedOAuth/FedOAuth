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
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL Patrick Uiterwijk BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

try:
    from flask import _app_ctx_stack as stack
except ImportError:
    from flask import _request_ctx_stack as stack

from fedora.client.fasproxy import FasProxyClient
from fedora.client import AuthError

from fas_openid import get_session


def _get_fasclient():
    ctx = stack.top
    if not hasattr(ctx, 'fasclient'):
        ctx.fasclient = FasProxyClient(
                                base_url = app.config['FAS_BASE_URL'], 
                                useragent = app.config['FAS_USER_AGENT'],
                                insecure = not app.config['FAS_CHECK_CERT']
                                )
    return ctx.fasclient

def logged_in():
    return 'user' in get_session()

def get(field):
    if not 'user' in get_session():
        return None
    if not field in get_session()['user']:
        return None
    return get_session()['user'][field]



def check_login(username, password):
    try:
        session_id, data = get_fasclient().login(username, password)
        return data.user
    except AuthError:
        return False
    except Exception, ex:
        log_warning('Error', {'message': 'An error occured while checking username/password: %s' % ex})
        return False

@app.route('/login/', methods=['GET','POST'])
def auth_login():
    if not 'next' in request.args and not 'next' in get_session():
        return redirect(url_for('view_main'))
    if 'next' in request.args:
        get_session()['next'] = request.args['next']
        get_session().save()
    if get_user() and not ('timeout' in get_session() and get_session()['timeout']): # We can also have "timeout" as of 0.4.0, indicating PAPE or application configuration requires a re-auth
        log_debug('Info', {'message': 'User tried to login but is already authenticated'})
        return redirect(get_session()['next'])
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if (not app.config['AVAILABLE_FILTER']) or (username in app.config['AVAILABLE_TO']):
            user = check_login(username, password)
            if user:
                log_info('Success', {'username': username, 'message': 'User authenticated succesfully'})
                user = user.toDict() # A bunch is not serializable...
                user['groups'] = [x['name'] for x in user['approved_memberships']]
                for key in user.keys():
                    if not key in USEFUL_FIELDS:
                        del user[key]
                get_session()['user'] = user
                get_session()['last_auth_time'] = time()
                get_session()['timeout'] = False
                get_session()['trust_root'] = ''
                get_session().save()
                return redirect(get_session()['next'])
            else:
                log_warning('Failure', {'username': username, 'message': 'User entered incorrect username or password'})
                flash(_('Incorrect username or password'))
        else:
            log_warning('Failure', {'username': username, 'message': 'Tried to login with an account that is not allowed to use this service'})
            flash(_('This service is limited to the following users: %(users)s', users=', '.join(app.config['AVAILABLE_TO'])))
    return render_template('auth_fas_login.html', trust_root=get_session()['trust_root'])
