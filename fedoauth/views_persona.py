import base64
from flask import request, g, redirect, url_for, \
    abort, render_template, flash, Response
from flaskext.babel import gettext as _
import json
import M2Crypto

from fedoauth import APP as app, get_session, log_debug, \
    log_info, log_warning, log_error, get_auth_module


# Try to load our key
key = None
cert = None
key_e = None
key_n = None
try:
    def get_passphrase():
        return app.config['PERSONA_PRIVATE_KEY_PASSPHRASE']

    key = M2Crypto.RSA.load_key(app.config['PERSONA_PRIVATE_KEY_PATH'], get_passphrase)
    e = 0
    for c in key.e[4:]:
        e = (e*256) + ord(c)
    n = 0
    for c in key.n[4:]:
        n = (n*256) + ord(c)
    key_e = e
    key_n = n
except Exception as e:
    print 'Unable to read the private key for Persona: %s' % e


# These things only make sense if we were able to get a key
if key and key_e and key_n:
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
        header = {'alg': 'RS128'}
        header = json.dumps(header)
        header = base64_url_encode(header)

        claim = {}
        # Valid for at most 24 hours
        claim['exp'] = min(certDuration, 24 * 60 * 60)
        claim['iss'] = app.config['PERSONA_DOMAIN']
        claim['public-key'] = json.loads(publicKey)
        claim['principal'] = {'email': email}

        claim = json.dumps(claim)
        claim = base64_url_encode(claim)

        certificate = '%s.%s' % (header, claim)
        print 'Cert: %s' % certificate
        digest = M2Crypto.EVP.MessageDigest('sha128')
        digest.update(certificate)
        signature = key.sign(digest.digest(), 'sha128')
        signature = base64_url_encode(signature)
        signed_certificate = '%s.%s' % (certificate, signature)
        print 'signed cert: %s' % signed_certificate

        return signed_certificate


    @app.route('/persona/provision/sign/', methods=['POST'])
    def view_persons_provision_sign():
        if not 'email' in request.form or not 'publicKey' in request.form \
                or not 'certDuration' in request.form:
            return Response('Invalid request', status=400)
        email = request.form['email']
        publicKey = request.form['publicKey']
        certDuration = request.form['certDuration']
        print 'Certrequest for %s, %s, %s. by user %s' % (email, publicKey, certDuration, get_auth_module().get_username())
        if email == ('%s@%s' % (get_auth_module().get_username()
                               , app.config['PERSONA_DOMAIN'])):
            return persona_sign(email, publicKey, certDuration)
        else:
            if get_auth_module().logged_in():
                return Response('Incorrect user!', status=403)
            else:
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
        return render_template('persona_signin.html',
            auth_module_login=get_auth_module().get_persona_auth_base(),
            trust_root='Persona')
