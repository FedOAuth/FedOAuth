from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash, Response

from model import FASOpenIDStore

from fas_openid import APP as app, FAS
from fas_openid.model import FASOpenIDStore

from flask_fas import fas_login_required

from fas_openid import openid_teams as teams

import openid
from openid.extensions import sreg
from openid.server.server import Server as openid_server
from openid.server import server
from openid.consumer import discover


def get_server():
    if not hasattr(g, 'openid_server'):
        g.openid_server = openid_server(FASOpenIDStore(), op_endpoint=app.config['OPENID_ENDPOINT'])
    return g.openid_server


def complete_url_for(func, **values):
    from urlparse import urljoin
    return urljoin(app.config['OPENID_ENDPOINT'], url_for(func, **values))

def get_claimed_id(username):
    return app.config['OPENID_IDENTITY_URL'] % username

def addSReg(request, response, user):
    sreg_req = sreg.SRegRequest.fromOpenIDRequest(request)
    
    sreg_data = { 'nickname'    : user.username
                , 'email'       : user.email
                , 'fullname'    : user.human_name
                , 'timezone'    : user.timezone
                }

    response.addExtension(sreg.SRegResponse.extractResponse(sreg_req, sreg_data))

def addTeams(request, response, groups):
    teams_req = teams.TeamsRequest.fromOpenIDRequest(request)
    teams_resp = teams.TeamsResponse.extractResponse(teams_req, groups)
    response.addExtension(teams_resp)

def addToSessionArray(array, value):
    if array in session:
        session[array].append(value)
    else:
        session[array] = [value]

def user_ask_trust_root(openid_request):
    if request.method == 'POST':
        decided = request.form['decided']
        if decided == 'Yes':
            addToSessionArray('TRUSTED_ROOTS', openid_request.trust_root)
        else:
            addToSessionArray('NON_TRUSTED_ROOTS', openid_request.trust_root)
        return redirect(request.url)
    # Get which stuff we will send
    sreg_req = sreg.SRegRequest.fromOpenIDRequest(request)
    teams_req = teams.TeamsRequest.fromOpenIDRequest(request)
    teams_resp = teams.TeamsResponse.extractResponse(teams_req, groups)
    # Show form
    return render_template('user_ask_trust_root.html'
                          , action              = request.url
                          , trust_root          = openid_request.trust_root
                          , sreg_required       = sreg_req.required
                          , sreg_optional       = sreg_req.optional
                          , sreg_policy_url     = sreg_req.policy_url
                          , sreg_value_nickname = g.fas_user.username
                          , sreg_value_email    = g.fas_user.email
                          , sreg_value_fullname = g.fas_user.human_name
                          , sreg_value_timezone = g.fas_user.timezone
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
            addSReg(openid_request, openid_response, g.fas_user)
            addTeams(openid_request, openid_response, g.fas_user.groups)
            return openid_respond(openid_response)
        elif authed == 1:
            # User needs to confirm trust root
            return user_ask_trust_root(openid_request)
        elif openid_request.immediate or authed == -1:
            return openid_respond(openid_request.answer(False))
        if g.fas_user is None:
            session['next'] = request.url
            return redirect(app.config['LOGIN_URL'])
        return 'Welcome, user! We hope you will visit us soon! <br /> Your details: %s' % g.fas_user
        pass    # TODO: CHECK THE REQUEST
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
    elif openid_request.trust_root in session['TRUSTED_ROOTS']:
        return 2
    elif openid_request.trust_root in session['NON_TRUSTED_ROOTS']:
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
    flash('You have been logged out')
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
                flash('Incorrect username or password')
        else:
            flash('This service is limited to the following users: %s' % (', '.join(app.config['AVAILABLE_TO'])))
    return render_template('login.html', title='Login')

@app.route('/test/')
@fas_login_required
def view_test():
    return render_template('index.html', title='Testing', text='TESTJE. User: %s' % g.fas_user)
