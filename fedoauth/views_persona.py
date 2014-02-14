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
import base64
from flask import request, g, redirect, url_for, \
    abort, render_template, flash, Response
from flaskext.babel import gettext as _
import json
import time
import M2Crypto

from fedoauth import APP as app, get_session, log_debug, \
    log_info, log_warning, log_error, get_auth_module


# Try to load our key
key = None
key_len = None
cert = None
key_e = None
key_n = None
digest_size = None
try:
    def get_passphrase(*args):
        return app.config['PERSONA_PRIVATE_KEY_PASSPHRASE']

    key = M2Crypto.RSA.load_key(app.config['PERSONA_PRIVATE_KEY_PATH'], get_passphrase)
    key_len = len(key)
    if key_len == 2048:
        digest_size = '256'
    else:
        raise Exception('Keys with size %i bits are not supported' % key_len)
    e = 0
    for c in key.e[4:]:
        e = (e*256) + ord(c)
    n = 0
    for c in key.n[4:]:
        n = (n*256) + ord(c)
    key_e = e
    key_n = n
except Exception as e:
    log_error('Unable to read the private key for Persona: %s' % e)


# These things only make sense if we were able to get a key
if key and key_len and digest_size and key_e and key_n:
    @app.route('/.well-known/browserid')
    def view_browserid():
        info = {}
        info['authentication'] = '/persona/sign_in/'
        info['provisioning'] = '/persona/provision/'
        info['public-key'] = {}

        info['public-key']['algorithm'] = 'RS'
        info['public-key']['n'] = str(key_n)
        info['public-key']['e'] = str(key_e)

        return Response(json.dumps(info),
                        mimetype='application/json')


    def base64_url_decode(input):
        input += '=' * (4 - (len(input) % 4))
        return base64.urlsafe_b64decode(input)


    def base64_url_encode(input):
        return base64.urlsafe_b64encode(input).replace('=', '')


    def persona_sign(email, publicKey, certDuration):
        header = {'alg': 'RS%s' % digest_size}
        header = json.dumps(header)
        header = base64_url_encode(header)

        claim = {}
        # Valid for at most 24 hours
        claim['iat'] = 1000 * int(time.time() - 10)
        claim['exp'] = 1000 * int(time.time() + \
                                    min(certDuration, 24 * 60 * 60))
        claim['iss'] = app.config['PERSONA_ISSUER']
        claim['public-key'] = json.loads(publicKey)
        claim['principal'] = {'email': email}
        claim_json = claim

        claim = json.dumps(claim)
        claim = base64_url_encode(claim)

        certificate = '%s.%s' % (header, claim)
        digest = M2Crypto.EVP.MessageDigest('sha%s' % digest_size)
        digest.update(certificate)
        signature = key.sign(digest.digest(), 'sha%s' % digest_size)
        signature = base64_url_encode(signature)
        signed_certificate = '%s.%s' % (certificate, signature)

        log_info('Success', {
            'email': email,
            'issuedAt': str(claim_json['iat']),
            'expiresAt': str(claim_json['exp']),
            'message': 'The user succesfully acquired a Persona certificate'})

        return signed_certificate


    @app.route('/persona/provision/sign/', methods=['POST'])
    def view_persons_provision_sign():
        if not 'email' in request.form or not 'publicKey' in request.form \
                or not 'certDuration' in request.form:
            return Response('Invalid request', status=400)
        email = request.form['email']
        publicKey = request.form['publicKey']
        certDuration = request.form['certDuration']
        if email == ('%s@%s' % (get_auth_module().get_username()
                               , app.config['PERSONA_DOMAIN'])):
            return persona_sign(email, publicKey, certDuration)
        else:
            if get_auth_module().logged_in():
                log_error('Failure', {
                    'email': email,
                    'username': get_auth_module().get_username(),
                    'message': 'User tried to get certificate for incorrect user'
                })
                return Response('Incorrect user!', status=403)
            else:
                log_error('Failure', {
                    'email': email,
                    'message': 'User tried to get certificate while not logged in'
                })
                return Response('Not signed in', status=401)


    @app.route('/persona/provision/')
    def view_persona_provision():
        user_email = 'INVALID'
        if get_auth_module().logged_in():
            user_email = '%s@%s' % (get_auth_module().get_username()
                                   , app.config['PERSONA_DOMAIN'])
        return render_template('persona_provision.html', user_email=user_email)


    @app.route('/persona/sign_in/')
    def view_persona_sign_in():
        get_session().delete()
        return render_template('persona_signin.html',
            auth_module_login=get_auth_module().get_persona_auth_base(),
            trust_root='Persona', domain=app.config['PERSONA_DOMAIN'],
            website_root=app.config['WEBSITE_ROOT'])
