from flask import request, g, redirect, url_for, \
    abort, render_template, flash, Response
from flaskext.babel import gettext as _
import json

from fedoauth import APP as app, get_session, log_debug, \
    log_info, log_warning, log_error, get_auth_module


@app.route('/.well-known/browserid')
def view_browserid():
    info = {}
    info['authentication'] = '/persona/sign_in/'
    info['provisioning'] = '/persona/provision/'
    info['public-key'] = {}

    info['public-key']['algorithm'] = ''
    info['public-key']['n'] = ''
    info['public-key']['e'] = ''

    return json.dumps(info)


@app.route('/persona/provision/')
def view_persona_provision():
    return render_template('persona_provision.html')


@app.route('/persona/sign_in/')
def view_persona_sign_in():
    return 'SIGNIN'
