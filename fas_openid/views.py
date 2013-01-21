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
                , 'dob'         : None
                , 'gender'      : None
                , 'postcode'    : None
                , 'country'     : None
                , 'language'    : None
                , 'timezone'    : user.timezone
                }

    response.addExtension(sreg.SRegResponse.extractResponse(sreg_req, sreg_data))

def addTeams(request, response, groups):
    teams_req = teams.TeamsRequest.fromOpenIDRequest(request)

    response.addExtension(teams.TeamsResponse.extractResponse(teams_req, groups))

@app.route('/', methods=['GET', 'POST'])
def view_main():
    try:
        openid_request = get_server().decodeRequest(request.values)
    except server.ProtocolError, openid_error:
        return openid_respond(openid_error)

    if openid_request is None:
        return render_template('index.html', text='MAIN PAGE, no OpenID request', openid_endpoint=app.config['OPENID_ENDPOINT'], yadis_url=complete_url_for('view_yadis')), 200, {'X-XRDS-Location': complete_url_for('view_yadis')}
    elif openid_request.mode in ['checkid_immediate', 'checkid_setup']:
        if isAuthorized(openid_request):
            openid_response = openid_request.answer(True, identity=get_claimed_id(g.fas_user.username), claimed_id=get_claimed_id(g.fas_user.username))
            addSReg(openid_request, openid_response, g.fas_user)
            addTeams(openid_request, openid_response, g.fas_user.groups)
            return openid_respond(openid_response)
        elif openid_request.immediate:
            return openid_respond(openid_request.answer(False))
        if g.fas_user is None:
            session['next'] = request.url
            return redirect(url_for('auth_login'))
        return 'Welcome, user! We hope you will visit us soon! <br /> Your details: %s' % g.fas_user
        pass    # TODO: CHECK THE REQUEST
    else:
        return openid_respond(get_server().handleRequest(openid_request))

def isAuthorized(openid_request):
    if g.fas_user is None:
        print 'not logged in'
        return False
    elif openid_request.idSelect():
        print 'idselect'
        return True     # Everyone is allowed to use the idSelect, since we return the correct computed endpoints
    elif openid_request.identity != get_claimed_id(g.fas_user.username):
        print 'Incorrect claimed id. Claimed: %s, correct: %s' % (openid_request.identity, get_claimed_id(g.fas_user.username))
        return False
    else:
        print 'Check here for user allowance...'
        return True

@app.route('/id/<username>/')
def view_id(username):
    return render_template('user.html', username=username, openid_endpoint=app.config['OPENID_ENDPOINT'], claimed_id=get_claimed_id(username), yadis_url=complete_url_for('view_yadis_id', username=username)), 200, {'X-XRDS-Location': complete_url_for('view_yadis_id', username=username)}


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
    return render_template('login.html')

@app.route('/test/')
@fas_login_required
def view_test():
    return render_template('index.html', text='TESTJE. User: %s' % g.fas_user)
