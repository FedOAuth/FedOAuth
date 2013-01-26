from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash, Response

from model import FASOpenIDStore

from fas_openid import APP as app, FAS, logger
from fas_openid.model import FASOpenIDStore

from flask_fas import fas_login_required

from fas_openid import openid_teams as teams

import openid
from openid.extensions import sreg
from openid.server.server import Server as openid_server
from openid.server import server
from openid.consumer import discover

from urlparse import urljoin

from flaskext.babel import gettext as _

from uuid import uuid4 as uuid

def get_server():
    if not hasattr(g, 'openid_server'):
        g.openid_server = openid_server(FASOpenIDStore(), op_endpoint=app.config['OPENID_ENDPOINT'])
    return g.openid_server


def complete_url_for(func, **values):
    return urljoin(app.config['OPENID_ENDPOINT'], url_for(func, **values))

def get_claimed_id(username):
    # The urljoin is so that we alway get <id>/ instead of both <id> and <id>/
    return urljoin(app.config['OPENID_IDENTITY_URL'] % username, '/')

def addSReg(request, response, user):
    sreg_req = sreg.SRegRequest.fromOpenIDRequest(request)
    sreg_data = { 'nickname'    : user.username
                , 'email'       : user.email
                , 'fullname'    : user.human_name
                , 'timezone'    : user.timezone
                }
    sreg_resp = sreg.SRegResponse.extractResponse(sreg_req, sreg_data)
    response.addExtension(sreg_resp)
    return sreg_resp.data

def addTeams(request, response, groups):
    teams_req = teams.TeamsRequest.fromOpenIDRequest(request)
    teams_resp = teams.TeamsResponse.extractResponse(teams_req, groups)
    response.addExtension(teams_resp)
    return teams_resp.teams

def addToSessionArray(array, value):
    if array in session:
        session[array].append(value)
        session.modified = True
    else:
        session[array] = [value]

def getSessionValue(key, default_value=None):
    if key in session:
        return session[key]
    else:
        return default_value

def user_ask_trust_root(openid_request):
    if request.method == 'POST':
        if 'decided_allow' in request.form:
            addToSessionArray('TRUSTED_ROOTS', openid_request.trust_root)
        else:
            addToSessionArray('NON_TRUSTED_ROOTS', openid_request.trust_root)
        return redirect(request.url)
    # Get which stuff we will send
    sreg_data = { 'nickname'    : g.fas_user.username
                , 'email'       : g.fas_user.email
                , 'fullname'    : g.fas_user.human_name
                , 'timezone'    : g.fas_user.timezone
                }
    sreg_req = sreg.SRegRequest.fromOpenIDRequest(openid_request)
    sreg_resp = sreg.SRegResponse.extractResponse(sreg_req, sreg_data)
    teams_req = teams.TeamsRequest.fromOpenIDRequest(openid_request)
    teams_resp = teams.TeamsResponse.extractResponse(teams_req, g.fas_user.groups)
    # Show form
    return render_template('user_ask_trust_root.html'
                          , action              = request.url
                          , trust_root          = openid_request.trust_root
                          , sreg_policy_url     = sreg_req.policy_url
                          , sreg_data           = sreg_resp.data
                          , teams_provided      = teams_resp.teams
                          )

@app.route('/', methods=['GET', 'POST'])
def view_main():
    try:
        openid_request = get_server().decodeRequest(request.values)
    except server.ProtocolError, openid_error:
        return openid_respond(openid_error)

    if openid_request is None:
        return render_template('index.html', title='Home', text='MAIN PAGE, no OpenID request', openid_endpoint=app.config['OPENID_ENDPOINT'], yadis_url=complete_url_for('view_yadis')), 200, {'X-XRDS-Location': complete_url_for('view_yadis')}
    elif openid_request.mode in ['checkid_immediate', 'checkid_setup']:
        authed = isAuthorized(openid_request)
        if authed == 2:
            openid_response = openid_request.answer(True, identity=get_claimed_id(g.fas_user.username), claimed_id=get_claimed_id(g.fas_user.username))
            sreg_info = addSReg(openid_request, openid_response, g.fas_user)
            teams_info = addTeams(openid_request, openid_response, g.fas_user.groups)
            logger.info('Succesful OpenID claiming. Logged in username: %(username)s. Claimed id: %(claimed)s. SReg data: %(sreg)s. Teams data: %(teams)s. Security level: %(seclvl)s' % {'username': g.fas_user.username, 'claimed': get_claimed_id(g.fas_user.username), 'sreg': sreg_info, 'teams': teams_info, 'seclvl': '1'})
            return openid_respond(openid_response)
        elif authed == 1:
            # User needs to confirm trust root
            return user_ask_trust_root(openid_request)
        elif authed == -1:
            logger.info('Trust-root was denied: %(trust_root)s for user: %(username)s' % {'trust_root': openid_request.trust_root, 'username': g.fas_user.username})
            return openid_respond(openid_request.answer(False))
        elif openid_request.immediate:
            logger.info('Trust-root requested checkid_immediate: %(trust_root)s' % {'trust_root': openid_request.trust_root})
            return openid_respond(openid_request.answer(False))
        if g.fas_user is None:
            session['next'] = request.url
            return redirect(app.config['LOGIN_URL'])
        else:
            logid = uuid().hex
            logger.error('[%(logid)s]A user tried to claim an ID that is not his own!!! Username: %(username)s. Claimed id: %(claimed_id)s. trust_root: %(trust_root)s' % {'username': g.fas_user.username, 'claimed_id': openid_request.identity, 'trust_root': openid_request.trust_root, 'logid': logid})
            return 'This is not your ID! If it is, please contact the administrators at admin@fedoraproject.org. Be sure to mention your logging ID: %(logid)s' % {'logid': logid}
    else:
        return openid_respond(get_server().handleRequest(openid_request))

def isAuthorized(openid_request):
    if g.fas_user is None:
        return 0
    elif (not openid_request.idSelect()) and (openid_request.identity != get_claimed_id(g.fas_user.username)):
        print 'Incorrect claimed id. Claimed: %s, correct: %s' % (openid_request.identity, get_claimed_id(g.fas_user.username))
        return 0
    elif openid_request.trust_root in app.config['TRUSTED_ROOTS']:
        return 2
    elif openid_request.trust_root in app.config['NON_TRUSTED_ROOTS']:
        return -1
    elif openid_request.trust_root in getSessionValue('TRUSTED_ROOTS', []):
        return 2
    elif openid_request.trust_root in getSessionValue('NON_TRUSTED_ROOTS', []):
        return -1
    else:
        # The user still needs to determine if he/she allows this trust root
        return 1

@app.route('/id/<username>/')
def view_id(username):
    return render_template('user.html', title='User page', username=username, openid_endpoint=app.config['OPENID_ENDPOINT'], claimed_id=get_claimed_id(username), yadis_url=complete_url_for('view_yadis_id', username=username)), 200, {'X-XRDS-Location': complete_url_for('view_yadis_id', username=username)}


@app.route('/yadis/<username>.xrds')
def view_yadis_id(username):
    return Response(render_template('yadis_user.xrds', openid_endpoint=app.config['OPENID_ENDPOINT'], claimed_id=get_claimed_id(username)), mimetype='application/xrds+xml')

@app.route('/yadis.xrds')
def view_yadis():
    return Response(render_template('yadis.xrds', openid_endpoint=app.config['OPENID_ENDPOINT']), mimetype='application/xrds+xml')

def openid_respond(openid_response):
    try:
        webresponse = get_server().encodeResponse(openid_response)
        return (webresponse.body, webresponse.code, webresponse.headers)
    except server.EncodingError, why:
        headers = {'Content-type': 'text/plain; charset=UTF-8'} 
        return why.response.encodeToKVForm(), 400, headers


@app.route('/logout/')
def auth_logout():
    if not g.fas_user:
        return redirect(url_for('view_main'))
    FAS.logout()
    session.clear()
    flash(_('You have been logged out'))
    return redirect(url_for('view_main'))

@app.route('/login/', methods=['GET','POST'])
def auth_login():
    if not 'next' in request.args and not 'next' in session:
        return redirect(url_for('view_main'))
    if 'next' in request.args:
        session['next'] = request.args['next']
    if g.fas_user:
        return redirect(session['next'])
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if (not app.config['AVAILABLE_FILTER']) or (username in app.config['AVAILABLE_TO']):
            if FAS.login(username, password):
                return redirect(session['next'])
            else:
                flash(_('Incorrect username or password'))
        else:
            flash(_('This service is limited to the following users: %(users)s', users=', '.join(app.config['AVAILABLE_TO'])))
    return render_template('login.html', title='Login')

@app.route('/test/')
@fas_login_required
def view_test():
    return render_template('index.html', title='Testing', text='TESTJE. User: %s' % g.fas_user)
