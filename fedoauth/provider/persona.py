# Copyright (C) 2014 Patrick Uiterwijk <patrick@puiterwijk.org>
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
import logging
from flask import request, render_template, Response
import json
import time
import M2Crypto

from fedoauth import APP
from fedoauth.utils import require_login
from fedoauth.auth.base import StandardAttributes

logger = logging.getLogger(__name__)
config = APP.config['AUTH_PROVIDER_CONFIGURATION'][__name__]


def get_issuer():
    urlroot = APP.config['GLOBAL']['url_root']
    end = None
    if ':' in urlroot[len('https://')]:
        end = urlroot.find(':', len('https://'))
    return urlroot[len('https://'):end]


if not APP.config['GLOBAL']['url_root'].startswith('https://'):
    raise Exception('To use Persona, the url_root MUST be https://')


# Try to load our key
key = None
key_len = None
cert = None
key_e = 0
key_n = 0
digest_size = None


def get_passphrase(*args):
    return config['private_key']['passphrase']

key = M2Crypto.RSA.load_key(config['private_key']['path'], get_passphrase)
key_len = len(key)
if key_len == 2048:
    digest_size = '256'
else:
    raise Exception('Keys with size %i bits are not supported' % key_len)
for c in key.e[4:]:
    key_e = (key_e*256) + ord(c)
for c in key.n[4:]:
    key_n = (key_n*256) + ord(c)


@APP.route('/.well-known/browserid')
def view_browserid():
    if 'domain' not in request.args:
        logger.debug('Invalid browserid request: no domain')
        return Response('Invalid request')
    domain = request.args['domain']
    if domain not in config['domains']:
        logger.error('Invalid browserid request for domain: %s', domain)
        return Response('Not willing to vouch for this domain')

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
    claim['exp'] = 1000 * int(time.time() +
                              min(certDuration, 24 * 60 * 60))
    # The issuer is our domain name
    claim['iss'] = get_issuer()
    claim['public-key'] = json.loads(publicKey)
    claim['principal'] = {'email': email}

    claim = json.dumps(claim)
    claim = base64_url_encode(claim)

    certificate = '%s.%s' % (header, claim)
    digest = M2Crypto.EVP.MessageDigest('sha%s' % digest_size)
    digest.update(certificate)
    signature = key.sign(digest.digest(), 'sha%s' % digest_size)
    signature = base64_url_encode(signature)
    signed_certificate = '%s.%s' % (certificate, signature)

    logger.debug('Issued a certificate for %s' % email)

    return signed_certificate


@APP.route('/persona/provision/sign/', methods=['POST'])
def view_persona_provision_sign():
    request.delete_transaction_after_request()
    if 'email' not in request.form or 'publicKey' not in request.form \
            or 'certDuration' not in request.form \
            or '@' not in request.form['email']:
        return Response('Invalid request', status=400)
    email = request.form['email']
    publicKey = request.form['publicKey']
    certDuration = request.form['certDuration']
    if not request.auth_module:
        logger.info('User tried to get cert while not logged in for: %s',
                    email)
        return Response('Not signed in', status=401)
    if request.auth_module.willing_to_sign_for_email(email):
        return persona_sign(email, publicKey, certDuration)
    else:
        logger.error('User tried to get certificate for non-signable email'
                     ' Username: %s.'
                     ' attempted: %s',
                     request.auth_module.get_username(),
                     email)
        return Response('Incorrect user!', status=403)


@APP.route('/persona/provision/')
def view_persona_provision():
    return render_template('persona_provision.html',
                           loggedin=request.auth_module is not None)


@APP.route('/persona/sign_in/')
def view_persona_sign_in():
    username = None
    domain = None
    if 'email' in request.args:
        email = request.args['email']
        if '@' in email:
            username = email[:email.find('@')]
            domain = email[email.find('@')+1:]
    require_login('Persona',
                  'view_persona_sign_in',
                  'view_persona_sign_in_failure',
                  username=username,
                  email_auth_domain=domain,
                  requested_attributes=[StandardAttributes.email])

    request.persist_transaction()

    return render_template('persona_sign_in.html')


@APP.route('/persona/sign_in/failure/')
def view_persona_sign_in_failure():
    return render_template('persona_sign_in_failure.html')
