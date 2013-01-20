from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash, Response

from model import FASOpenIDStore

from fas_openid import APP as app, FAS
from fas_openid.model import FASOpenIDStore

from flask_fas import fas_login_required

import openid
from openid.extensions import sreg
from openid.server.server import Server as openid_server
from openid.server import server
from openid.consumer import discover


def get_server():
    if not hasattr(g, 'openid_server'):
        g.openid_server = openid_server(FASOpenIDStore(), op_endpoint=app.config['OPENID_ENDPOINT'])
    return g.openid_server


@app.route('/')
def view_main():
    try:
        openid_request = get_server().decodeRequest(request.args)
    except server.ProtocolError, openid_error:
        return openid_respond(openid_error)

    if openid_request is None:
        return render_template('index.html', text='MAIN PAGE, no OpenID request'), 200, {'X-XRDS-Location': url_for('yadis')}
    elif openid_request.mode in ['checkid_immediate', 'checkid_setup']:
        return 'TODO'
        pass    # TODO: CHECK THE REQUEST
    else:
        return openid_respond(get_server().handleRequest(openid_request))

@app.route('/yadis/')
def view_yadis():
    return Response(render_template('yadis.xrds'), mimetype='application/xrds+xml')

def openid_respond(response):
    try:
        webresponse = self.openid.encodeResponse(openid_response)
        return (webresponse.body, webresponse.status, webresponse.headers)
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
        result = FAS.login(username, password)
        if result:
            return redirect(session['next'])
        else:
            flash('Incorrect username or password')
    return render_template('login.html')

@app.route('/test/')
@fas_login_required
def view_test():
    return render_template('index.html', text='TESTJE. User: %s' % g.fas_user)
