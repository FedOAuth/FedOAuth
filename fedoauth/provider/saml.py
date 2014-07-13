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
#
# Needed because we import the system openid stuff
from __future__ import absolute_import

import json
import logging

from flask import request, redirect, \
    render_template, Response

from fedoauth import APP, get_loaded_auth_modules
from fedoauth.model import Remembered
from fedoauth.utils import no_cache, complete_url_for, require_login
from fedoauth.auth.base import StandardAttributes

from saml2 import BINDING_HTTP_REDIRECT, BINDING_URI, BINDING_HTTP_ARTIFACT, \
    BINDING_HTTP_POST, BINDING_SOAP
from saml2.saml import NAMEID_FORMAT_TRANSIENT, NAMEID_FORMAT_PERSISTENT
from saml2.metadata import create_metadata_string
from saml2.sigver import verify_redirect_signature, encrypt_cert_from_item, cert_from_instance
from saml2.server import Server as SamlServer
from saml2.response import IncorrectlySigned
from saml2.config import Config as SamlConfig
from saml2.authn_context import AuthnBroker, UNSPECIFIED, authn_context_class_ref


logger = logging.getLogger(__name__)
config = APP.config['AUTH_PROVIDER_CONFIGURATION'][__name__]


AUTHN_BROKER = AuthnBroker()
AUTHN_BROKER.add(authn_context_class_ref(UNSPECIFIED), 'unspecified')


def get_saml_config():
    # TODO: Build this from the FedOAuth config
    config = {}
    config['debug'] = 1
    config['entityid'] = 'FedOAuth-IdP'
    config['name'] = 'FedOAuth IdP'
    config['cert_file'] = './saml.crt'
    config['key_file'] = './saml.pem'
    config['valid_for'] = 0.01
    config['disable_ssl_certificate_validation'] = True
    config['xmlsec_binary'] = '/usr/bin/xmlsec1'
    config['verify_ssl_cert'] = False
    config['ca_certs'] = '/etc/pki/ca-trust/extracted/openssl/ca-bundle.trust.crt'
    config['organization'] = {'name': 'FedOAuth Development',
                              'display_name': 'FedOAuth Development, Inc.',
                              'url': 'http://fedoauth.org'}
    config['contact_person'] = [{'contact_type': 'technical',
                                 'given_name': 'FedOAuth Technical',
                                 'email_address': 'devnull@fedoauth.org'},
                                 {'contact_type': 'support',
                                  'given_name': 'FedOAuth Support',
                                  'email_address': 'devnull@fedoauth.org'}
                               ]
    config['metadata'] = {
        'local': ['consumer.xml']
    }

    BASE = APP.config['GLOBAL']['url_root']
    config['service'] = {'idp': {
                            'name': 'FedOAuth IdP',
                            'want_authn_requests_only_with_valid_cert': False,
                            'want_authn_requests_signed': False,
                            'sign_assertion': True,
                            'sign_response': True,
                            'encrypt_assertion': False,
                            'verify_encrypt_cert': None,
                            'endpoints': {
                                'single_sign_on_service': [
                                    ('%s/saml/sso/redirect/' % BASE, BINDING_HTTP_REDIRECT),
                                    ('%s/saml/sso/post/' % BASE, BINDING_HTTP_POST),
                                    ('%s/saml/sso/art/' % BASE, BINDING_HTTP_ARTIFACT),
                                ],
                                'single_logout_service': [
                                    ('%s/saml/slo/soap/' % BASE, BINDING_SOAP),
                                    ('%s/saml/slo/post/' % BASE, BINDING_HTTP_POST),
                                    ('%s/saml/slo/redirect/' % BASE, BINDING_HTTP_REDIRECT),
                                ]},
                            # TODO: Move this to database
                            #'subject_data': ('identdb', 'fedoauth.provider.saml.FedOAuthIdentDB'),
                            'subject_data': './test.ident',
                            'name_id_format': [NAMEID_FORMAT_TRANSIENT,
                                               NAMEID_FORMAT_PERSISTENT]
                         }
                        }

    # Wrap in samlconfig, so we get some blank values for free
    samlconfig = SamlConfig()
    samlconfig.load(config)
    return samlconfig


@APP.route('/saml/metadata/')
def view_saml_metadata():
    config = get_saml_config()

    return no_cache(Response(create_metadata_string(None,
                                                    config,
                                                    None,
                                                    config.cert_file,
                                                    config.key_file,
                                                    config.entityid,
                                                    config.name,
                                                    True),
                             mimetype='text/xml'))


# Implement the actual request functions on a method not unlike the pySaml2 example IdP
# So we are using classes here, so we can easily reuse functions across services
class SAMLUIDCache(object):
    # TODO: Migrate this to a database-backed store
    def __init__(self):
        self.user2uid = {}
        self.uid2user = {}


class Service(object):
    instance = None
    @classmethod
    def get_instance(cls):
        if cls.instance == None:
            cls.instance = cls()
        return cls.instance
    
    def __init__(self):
        self.IDP = SamlServer(config=get_saml_config(), cache=SAMLUIDCache(), stype='idp')

    def artifact(self, **kwargs):
        logger.debug('SSO Artifact')
        saml_msg = request.values
        if not saml_msg:
            return 'Missing query', 400
        request = self.IDP.artifact2message(saml_msg['SAMLart'], 'spsso')
        return self.do(request, BINDING_HTTP_ARTIFACT, saml_msg.get('RelayState', ''), **kwargs)

    def redirect(self, **kwargs):
        logger.debug('SAML Generic Redirect')
        return self.handle_message(request.args, BINDING_HTTP_REDIRECT, **kwargs)

    def post(self, **kwargs):
        logger.debug('SAML Generic POST')
        return self.handle_message(request.values, BINDING_HTTP_POST, **kwargs)

    def soap(self, **kwargs):
        logger.debug('SAML Generic SOAP')
        soap_values = {'SAMLRequest': request.data,
                       'RelayState': ''}
        return self.operation(soap_values, BINDING_SOAP, **kwargs)

    def operation(self, saml_msg, binding, encrypt_cert=None, **kwargs):
        if not saml_msg or not 'SAMLRequest' in saml_msg:
            return 'Error parsing request or no request', 400
        else:
            return self.do(saml_msg['SAMLRequest'], binding,
                           saml_msg.get('RelayState', ''),
                           encrypt_cert=encrypt_cert, **kwargs)
    handle_message = operation

    def do(self, query, binding, relay_state='', encrypt_cert=None, **kwargs):
        logger.error('Handling do with query=%s, binding=%s, relay_state=%s, encrypt_cert=%s, kwargs=%s', query, binding, relay_state, encrypt_cert, kwargs)
        return 'SAML GENERIC DO'


class SSO(Service):
    def handle_message(self, saml_msg, binding, **kwargs):
        logger.info('SSO handle_message')

        req_info = None

        # Check if we returned from an auth
        if ('%s_msg' % __name__) in request.transaction:
            saml_msg = request.transaction['%s_msg' % __name__]
        else:
            request.transaction['%s_msg' % __name__] = saml_msg

        try:
            logger.info('Got binding: %s', binding)
            req_info = self.IDP.parse_authn_request(saml_msg['SAMLRequest'],
                                                    binding)
        except IncorrectlySigned:
            return 'Message signature verification failure', 400

        if 'SigAlg' in saml_msg and 'signature' in saml_msg:
            logging.info('Signed request')
            issuer = req_info.message.issuer.text
            _certs = self.IDP.metadata.certs(issuer, 'any', 'signing')
            verified_ok = False
            for cert in _certs:
                if verify_redirect_signature(saml_msg, cert):
                    verified_ok = True
                    break
            return 'verified'
            if not verified_ok:
                return 'Message signature verification failure', 400

        # Force auth modules to not use preauth
        #  This way, we always have a fresh session
        if req_info.message.force_authn:
            request.force_no_preauth()

        entry_view_name = None
        if binding == BINDING_HTTP_POST:
            entry_view_name = 'view_saml_sso_post'
        else:
            entry_view_name = 'view_saml_sso_redirect'

        logger.debug('Entry view: %s', entry_view_name)

        encrypt_cert = encrypt_cert_from_item(
            req_info.message)
        if not encrypt_cert:
            # Try this other solution as well
            # Temporary fix for https://github.com/rohe/pysaml2/pull/128
            certs = cert_from_instance(req_info.message)
            if len(certs) > 0:
                encrypt_cert = certs[0]

            if encrypt_cert is not None:
                if encrypt_cert.find("-----BEGIN CERTIFICATE-----\n") == -1:
                    encrypt_cert = "-----BEGIN CERTIFICATE-----\n" + encrypt_cert
                if encrypt_cert.find("-----END CERTIFICATE-----\n") == -1:
                    encrypt_cert = encrypt_cert + "\n-----END CERTIFICATE-----\n"

        if not 'cancelled' in kwargs:
            # If we cancelled, we don't need to auth anymore, and we'll abort in the next phase
            require_login(req_info.sender(),
                          entry_view_name,
                          '%s_failed' % entry_view_name)

        return self.operation(saml_msg, binding, encrypt_cert, **kwargs)

    def verify_request(self, query, binding):
        req_info = self.IDP.parse_authn_request(query, binding)
        logger.info('Parsed OK')
        authn_req = req_info.message
        logger.info('Authn req: %s', authn_req)
        binding_out = None
        destination = None
        try:
            binding_out, destination = self.IDP.pick_binding('assertion_consumer_service',
                                                             entity_id=authn_req.issuer.text,
                                                             request=authn_req)
        except Exception, ex:
            logger.error('Could not find receiver endpoint: %s', ex)
            raise

        logger.debug('Binding: %s, destination: %s', binding_out, destination)

        resp_args = {}
        
        try:
            resp_args = self.IDP.response_args(authn_req)
            _resp = None
        except UnknownPrincipal, excp:
            _resp = self.IDP.create_error_response(authn_req.id,
                                                   destination, excp, sign=True)
        except UnsupportedBinding, excp:
            _resp = self.IDP.create_error_response(authn_req.id,
                                                   destination, excp, sign=True)

        return resp_args, binding_out, destination, _resp

    def do(self, query, binding_in, relay_state='', encrypt_cert=None, **kwargs):
        if not query:
            logger.info('Missing query')
            return 'Unknown user', 401

        resp_args = None
        binding_out = None
        destination = None
        _resp = None
        try:
            resp_args, binding_out, destination, _resp = self.verify_request(query, binding_in)
        except Exception, excp:
            logger.error('Unknown error while verifying: %s', excp)
            return ('UnknownError: %s' % excp), 500

        logger.debug('resp_args: %s, binding_out: %s, destination: %s, _resp: %s',
                     resp_args, binding_out, destination, _resp)

        if not _resp:
            if 'cancelled' in kwargs:
                # User cancelled, let's generate a denial
                _resp = self.IDP.create_error_response(in_response_to=resp_args['in_response_to'],
                                                       destination=resp_args['destination'],
                                                       info=('401', 'Not authenticated'),
                                                       sign=True)
            else:
                identity = {}
                identity['something'] = 'values'
                identity['bar'] = 'foobar'

                try:
                    _resp = self.IDP.create_authn_response(
                        identity=identity, userid='BOE', #  name_id='BOE123',
                        authn=AUTHN_BROKER['1'], encrypt_cert=encrypt_cert,
                        **resp_args)
                except Exception, excp:
                    logging.error('Unknown error while creating response: %s', excp)
                    return ('UnknownError: %s' % excp), 500

        logger.info('AuthNResponse: %s', _resp)
        http_args = self.IDP.apply_binding(binding_out,
                                           _resp, destination,
                                           relay_state, response=True)

        logger.debug('HTTPargs: %s' % http_args)
        if binding_out == BINDING_HTTP_ARTIFACT:
            # TODO:
            return 'Redirect()'
        else:
            return ' '.join(http_args['data']), http_args.get('status', 200), http_args['headers']

class SLO(Service):
    def do(self, request, binding, relay_state='', encrypt_cert=None, **kwargs):
        logger.info('SLO do')
        req_info = None

        try:
            req_info = self.IDP.parse_logout_request(request, binding)
        except Exception, exc:
            logger.error('Bad request: %s', exc)
            return 'Bad request', 400

        if req_info.message.name_id:
            logger.info('Name_id: %s', req_info.message.name_id)
            lid = self.IDP.ident.find_local_id(req_info.message.name_id)
            logger.info('Local ID: %s', lid)

            for auth_module in get_loaded_auth_modules():
                auth_module.force_logout()

            # TODO: Do the actual logout of sessions with this name_id

        resp = self.IDP.create_logout_response(req_info.message, [binding], sign=False)
        signed_resp = self.IDP.create_logout_response(req_info.message, [binding], sign=True)

        http_args = None
        try:
            http_args = self.IDP.apply_binding(binding, signed_resp, resp.destination, relay_state=relay_state, response=True)
        except Exception, exc:
            logger.error('ServiceError: %s', exc)
            return 'ServiceError', 500

        if binding == BINDING_HTTP_REDIRECT:
            http_args['status'] = 302

        return ' '.join(http_args['data']), http_args.get('status', 200), http_args['headers']


# Routing happens here
## Single Signon Service
@APP.route('/saml/sso/redirect/')
def view_saml_sso_redirect():
    return SSO.get_instance().redirect()
@APP.route('/saml/sso/post/', methods=['GET', 'POST'])
def view_saml_sso_post():
    return SSO.get_instance().post()
@APP.route('/saml/sso/art/')
def view_saml_sso_artifact():
    return SSO.get_instance().artifact()
@APP.route('/saml/sso/post/failed/')
def view_saml_sso_post_failed():
    return SSO.get_instance().post(cancelled=True)
@APP.route('/saml/sso/redirect/failed/')
def view_saml_sso_redirect_failed():
    return SSO.get_instance().redirect(cancelled=True)

## Single Logout Service
@APP.route('/saml/slo/soap/')
def view_saml_slo_soap():
    return SLO.get_instance().soap()
@APP.route('/saml/slo/post/', methods=['POST'])
def view_saml_slo_post():
    return SLO.get_instance().post()
@APP.route('/saml/slo/redirect/')
def view_saml_slo_redirect():
    return SLO.get_instance().redirect()
