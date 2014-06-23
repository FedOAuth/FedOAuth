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
from openid.extensions import sreg
from openid.extensions import ax
from openid.extensions import pape
from openid.server.server import Server as openid_server
from openid import oidutil
from openid.server import server
import openid_teams.teams as teams
import openid_cla.cla as cla
try:
    from flaskext.babel import gettext as _
except ImportError, ie:
    from flask.ext.babel import gettext as _

from fedoauth import APP, get_auth_module_by_name
from fedoauth.model import OpenIDStore, Remembered
from fedoauth.utils import no_cache, complete_url_for, require_login
from fedoauth.auth.base import StandardAttributes


logger = logging.getLogger(__name__)
config = APP.config['AUTH_PROVIDER_CONFIGURATION'][__name__]


openid_server_instance = None

SREG_ATTRIBUTES = [StandardAttributes.nickname,
                   StandardAttributes.email,
                   StandardAttributes.fullname,
                   StandardAttributes.dob,
                   StandardAttributes.gender,
                   StandardAttributes.postalcode,
                   StandardAttributes.country,
                   StandardAttributes.language,
                   StandardAttributes.timezone]

# This is a mapping from AX type-uri to attribute keys
# Sources:
# http://openid.net/specs/openid-attribute-properties-list-1_0-01.html
# http://fedoauth.org/openid/schema/
AX_WELLKNOWN = {
    'http://schema.openid.net/namePerson': StandardAttributes.fullname,
    'http://schema.openid.net/contact/email': StandardAttributes.email,
    'http://axschema.org/namePerson': StandardAttributes.fullname,
    'http://axschema.org/namePerson/first': StandardAttributes.firstname,
    'http://axschema.org/namePerson/last': StandardAttributes.lastname,
    'http://axschema.org/namePerson/friendly': StandardAttributes.nickname,
    'http://axschema.org/contact/email': StandardAttributes.email,
    'http://openid.net/schema/namePerson/first': StandardAttributes.firstname,
    'http://openid.net/schema/namePerson/last': StandardAttributes.lastname,
    'http://openid.net/schema/namePerson/friendly':
        StandardAttributes.nickname,
    'http://openid.net/schema/gender': StandardAttributes.gender,
    'http://openid.net/schema/language/pref': StandardAttributes.language,
    'http://fedoauth.org/openid/schema/GPG/keyid':
        StandardAttributes.gpg_keyid,
    'http://fedoauth.org/openid/schema/SSH/key': StandardAttributes.ssh_key}


def get_server():
    global openid_server_instance
    if openid_server_instance is None:
        openid_server_instance = openid_server(
            OpenIDStore(),
            op_endpoint='%s/openid/' % APP.config['GLOBAL']['url_root'])
    return openid_server_instance


def get_claimed_id(username):
    identity = config['identity_url_pattern'] % {'username': username}
    # This is so we get one unique identiy (the one WITH trailing slash)
    if not identity.endswith('/'):
        identity = identity + '/'
    return identity


def addSReg(openid_request, openid_response):
    sreg_req = sreg.SRegRequest.fromOpenIDRequest(openid_request)
    sreg_data = request.auth_module.get_attributes(SREG_ATTRIBUTES)
    sreg_resp = sreg.SRegResponse.extractResponse(sreg_req, sreg_data)
    if openid_response:
        openid_response.addExtension(sreg_resp)
    return sreg_resp.data


def addAX(openid_request, openid_response):
    ax_req = ax.FetchRequest.fromOpenIDRequest(openid_request)
    if ax_req is None:
        return {}
    ax_resp = ax.FetchResponse(ax_req)
    for type_uri, attribute in ax_req.requested_attributes.iteritems():
        lookup = type_uri
        if lookup in AX_WELLKNOWN.keys():
            lookup = AX_WELLKNOWN[type_uri]
        try:
            value = request.auth_module.get_attribute(lookup)
            ax_resp.addValue(type_uri, value)
        except:
            pass
    if openid_response:
        openid_response.addExtension(ax_resp)
    ax_data = {}
    for key in ax_resp.data.keys():
        display = key
        if key in AX_WELLKNOWN.keys():
            display = AX_WELLKNOWN[key].__str__()
        for value in ax_resp.data[key]:
            ax_data[display] = value
    return ax_data


def addPape(openid_request, openid_response):
    auth_time = request.auth_module.last_loggedin(). \
        strftime('%Y-%m-%dT%H:%M:%SZ')
    auth_policies = []
    auth_levels = {}
    auth_levels[pape.LEVELS_NIST] = 2

    if request.auth_module.used_multi_factor():
        auth_policies.append(pape.AUTH_MULTI_FACTOR)
        if request.auth_module.used_multi_factor_physical():
            auth_policies.append(pape.AUTH_MULTI_FACTOR_PHYSICAL)
            if request.auth_module.used_phishing_resistant():
                auth_policies.append(pape.AUTH_PHISHING_RESISTANT)
                auth_levels[pape.LEVELS_NIST] = 3
    else:
        auth_policies.append(pape.AUTH_NONE)

    pape_resp = pape.Response(
        auth_policies=auth_policies,
        auth_time=auth_time,
        auth_levels=auth_levels)
    if openid_response:
        openid_response.addExtension(pape_resp)
    return auth_levels[pape.LEVELS_NIST]


def addTeams(openid_request, openid_response):
    teams_req = teams.TeamsRequest.fromOpenIDRequest(openid_request)
    if teams_req.requested == []:
        return []
    groups = request.auth_module.get_groups()
    if '_FAS_ALL_GROUPS_' in teams_req.requested and \
            config['handle_magic_groups_value']:
        # We will send all groups the user is a member of
        teams_req.requested = groups
    teams_resp = teams.TeamsResponse.extractResponse(teams_req, groups)
    if openid_response:
        openid_response.addExtension(teams_resp)
    return teams_resp.teams


def addCLAs(openid_request, openid_response):
    cla_req = cla.CLARequest.fromOpenIDRequest(openid_request)
    if cla_req.requested == []:
        return []
    cla_resp = cla.CLAResponse.extractResponse(cla_req,
                                               request.auth_module.get_clas()
                                               )
    if openid_response:
        openid_response.addExtension(cla_resp)
    return cla_resp.clas


@APP.route('/openid/id/<username>/')
def view_openid_id(username):
    return render_template(
        'openid_user.html',
        username=username,
        claimed_id=get_claimed_id(username),
        yadis_url=complete_url_for('view_openid_yadis_id',
                                   username=username)
    ),
    200,
    {'X-XRDS-Location':
     complete_url_for('view_openid_yadis_id', username=username),
     'Cache-Control': 'no-cache, must-revalidate',
     'Pragma': 'no-cache',
     'Expires': 'Sat, 26 Jul 1997 05:00:00 GMT'}


@APP.route('/openid/yadis/<username>.xrds')
def view_openid_yadis_id(username):
    return no_cache(Response(render_template('openid_yadis_user.xrds',
                    claimed_id=get_claimed_id(username)),
                    mimetype='application/xrds+xml'))


@APP.route('/openid/yadis.xrds')
def view_openid_yadis():
    return no_cache(Response(render_template('openid_yadis.xrds'),
                    mimetype='application/xrds+xml'))


def generate_openid_response(openid_request):
    username = request.auth_module.get_username()
    openid_response = openid_request.answer(
        True,
        identity=get_claimed_id(username),
        claimed_id=get_claimed_id(username)
    )
    addSReg(openid_request, openid_response)
    addAX(openid_request, openid_response)
    addTeams(openid_request, openid_response)
    addCLAs(openid_request, openid_response)
    addPape(openid_request, openid_response)
    return openid_response


@APP.route('/api/v1/', methods=['POST'])
def view_openid_api_v1_wrapper():
    return json.dumps(view_openid_api_v1())


def view_openid_api_v1():
    values = request.form
    openid_request = None
    try:
        openid_request = get_server().decodeRequest(values)
    except:
        return {'success': False,
                'status': 400,
                'message': 'Invalid request'
                }
    if not openid_request:
        return {'success': False,
                'status': 400,
                'message': 'Invalid request'
                }

    # First check if we were already authenticated
    # (Kerberos etc...)
    if not request.auth_module:
        if 'auth_module' not in values:
            return {'success': False,
                    'status': 400,
                    'message': 'No auth module selected'
                    }
        auth_module = get_auth_module_by_name(values['auth_module'])
        if not auth_module:
            return {'success': False,
                    'status': 400,
                    'message': 'Unknown authentication module'
                    }
        try:
            valid = auth_module.authenticate_api(values)
            if isinstance(valid, dict):
                valid['transaction'] = request.transaction_id
                valid['success'] = False
                return valid
        except Exception, ex:
            logger.warning('Authentication with auth module failed: %s', ex)

    if not request.auth_module:
        return {'success': False,
                'status': 403,
                'message': 'Authentication failed'
                }
    openid_response = generate_openid_response(openid_request)

    # Sign and return
    response = get_server().signatory.sign(openid_response).toPostArgs()
    return {'success': True,
            'response': response}


def openid_respond(openid_response):
    request.delete_transaction_after_request()
    try:
        webresponse = get_server().encodeResponse(openid_response)
        # This is a VERY ugly hack, but is required because the version of
        # python-openid in EPEL6 does not use the auto-submit encoder, but
        # only the toFormMarkup encoder.....
        if '<form' in webresponse.body and 'onload' not in webresponse.body:
            webresponse.body = oidutil.autoSubmitHTML(webresponse.body)
        logger.debug('Responding with :%s', webresponse)
        return (webresponse.body, webresponse.code, webresponse.headers)
    except server.EncodingError, why:
        logger.warning('Unable to respond with response: %s', why)
        headers = {'Content-type': 'text/plain; charset=UTF-8'}
        return why.response.encodeToKVForm(), 400, headers


@APP.route('/openid/failure/')
def view_openid_main_failure():
    values = None
    if ('%s_values' % __name__) in request.transaction:
        values = request.transaction['%s_values' % __name__]

    openid_request = None
    try:
        openid_request = get_server().decodeRequest(values)
    except server.ProtocolError, openid_error:
        return openid_respond(openid_error)

    if openid_request is None:
        return redirect(complete_url_for('view_main'))

    logger.debug('User cancelled signin')

    return openid_respond(openid_request.answer(False))


@APP.route('/openid/', methods=['GET', 'POST'])
def view_openid_main():
    values = None
    save_values = False
    if 'openid.mode' in request.values:
        values = request.values
        save_values = True
    elif ('%s_values' % __name__) in request.transaction:
        values = request.transaction['%s_values' % __name__]

    openid_request = None
    try:
        openid_request = get_server().decodeRequest(values)
    except server.ProtocolError, openid_error:
        return openid_respond(openid_error)

    if openid_request is None:
        return redirect(complete_url_for('view_main', err='no-transaction'))

    # Handle request
    if openid_request.mode == 'checkid_setup':
        # Check everything
        if save_values:
            # We might need to authenticate, so save everything
            request.transaction['%s_values' % __name__] = request.values
            request.save_transaction()

        require_login(openid_request.trust_root,
                      'view_openid_main',
                      'view_openid_main_failure')

        response = openid_checkid(openid_request)
        if response is True:
            return openid_respond(generate_openid_response(openid_request))
        elif response is False:
            return openid_respond(openid_request.answer(False))
        else:
            # Might be a web response or anything
            return response
    elif openid_request.mode == 'checkid_immediate':
        # The RP asked us to answer immediately, let's.
        if not request.auth_module:
            return openid_respond(openid_request.answer(False))

        response = openid_checkid(openid_request)
        if response is True:
            return openid_respond(generate_openid_response(openid_request))
        else:
            return openid_respond(openid_request.answer(False))
    else:
        # OpenID internal stuff
        return openid_respond(get_server().handleRequest(openid_request))


def openid_checkid(openid_request):
    # Assumption: we are logged in, so request.auth_module is valid
    # Return True to get an automatically signed response to be returned
    # In immediate, return anything else for failure response
    # In non-immediate, anything else will be returned as-is to the browser
    if not openid_request.idSelect() and \
            get_claimed_id(
                request.auth_module.get_username()
            ) != openid_request.identity:
        return 'NOT YOUR IDENTITY!'
    if openid_request.trust_root in config['non_trusted_roots']:
        logger.warning('Blacklisted trustroot attempted: %s',
                       openid_request.trust_root)
        return False
    if openid_request.trust_root in config['trusted_roots']:
        return True
    # We should check if the user accepts this trust_root
    if Remembered.getremembered('OpenIDAllow',
                                request.auth_module.full_name,
                                request.auth_module.get_username(),
                                openid_request.trust_root) is not None:
        logger.debug('User previously marked root as remembered trusted')
        return True
    elif request.method == 'POST' and 'form_filled' in request.form and \
            'decided_allow' in request.form:
        rememberForDays = request.form.get('rememberForDays', '0')
        try:
            rememberForDays = int(rememberForDays)
        except:
            rememberForDays = 0
        if rememberForDays < 0 or rememberForDays > 7:
            # They selected another option. We don't want either
            rememberForDays = 0
        if rememberForDays != 0:
            Remembered.rememberForDays('OpenIDAllow',
                                       rememberForDays,
                                       None,
                                       request.auth_module.full_name,
                                       request.auth_module.get_username(),
                                       openid_request.trust_root)
        return True
    elif request.method == 'POST' and 'form_filled' in request.form:
        logger.debug('User chose not to trust trustroot')
        return False
    else:
        # Show the user the authorization form
        sreg_req = sreg.SRegRequest.fromOpenIDRequest(openid_request)
        sreg_data = addSReg(openid_request, None)
        ax_data = addAX(openid_request, None)
        teams_data = addTeams(openid_request, None)
        clas_data = addCLAs(openid_request, None)

        # Hide this
        sreg_data.update(ax_data)

        data = []
        for field in sreg_data:
            data.append({'text': field,
                         'value': sreg_data[field]})

        # Sort these functions
        data.sort()

        for team in teams_data:
            data.append({'text': _('Group'),
                         'value': team})

        if clas_data != []:
            data.append({'text': _('FPCA Completed'),
                         'value': _('True')})

        return render_template(
            'openid_user_ask_trust_root.html',
            action=complete_url_for('view_openid_main',
                                    transaction=request.transaction_id),
            trust_root=openid_request.trust_root,
            sreg_policy_url=sreg_req.policy_url or _('None provided'),
            data=data)
