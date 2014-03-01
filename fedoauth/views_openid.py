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
from time import time
from datetime import datetime
import json
import sys
from urlparse import urljoin
from uuid import uuid4 as uuid

from flask import Flask, request, g, redirect, url_for, \
    abort, render_template, flash, Response
import openid
from openid.extensions import sreg
from openid.extensions import pape
from openid.server.server import Server as openid_server
from openid.server import server
from openid.consumer import discover
import openid_teams.teams as teams
import openid_cla.cla as cla
from flaskext.babel import gettext as _

from fedoauth import APP as app, get_session, log_debug, \
    log_info, log_warning, log_error, get_auth_module
from fedoauth.model import FedOAuthOpenIDStore
from fedoauth.utils import addToSessionArray, getSessionValue, no_cache, \
    complete_url_for

# Possible AUTH results
AUTH_NOT_LOGGED_IN = 0
AUTH_TIMEOUT = 1
AUTH_INCORRECT_IDENTITY = 2
AUTH_OK = 3
AUTH_TRUST_ROOT_NOT_OK = 4
AUTH_TRUST_ROOT_ASK = 5
AUTH_TRUST_ROOT_CONFIG_NOT_OK = 6


CLA_GROUPS = {'cla_click': cla.CLA_URI_FEDORA_CLICK,
              'cla_dell': cla.CLA_URI_FEDORA_DELL,
              'cla_done': cla.CLA_URI_FEDORA_DONE,
              'cla_fedora': cla.CLA_URI_FEDORA_FEDORA,
              'cla_fpca': cla.CLA_URI_FEDORA_FPCA,
              'cla_ibm': cla.CLA_URI_FEDORA_IBM,
              'cla_intel': cla.CLA_URI_FEDORA_INTEL,
              'cla_redhat': cla.CLA_URI_FEDORA_REDHAT
              }


openid_server_instance = None
def get_server():
    global openid_server_instance
    if openid_server_instance is None:
        openid_server_instance = openid_server(
            FedOAuthOpenIDStore(), op_endpoint=app.config['WEBSITE_ROOT'])
    return openid_server_instance


def filter_cla_groups(groups):
    return [group for group in groups if not group in CLA_GROUPS.keys()]


def get_cla_uris(groups):
    return [CLA_GROUPS[group]
            for group in groups if group in CLA_GROUPS.keys()]


def get_claimed_id(username):
    identity = app.config['OPENID_IDENTITY_URL'] % {'username': username}
    if not app.config['OPENID_IDENTITY_URL'].endswith('/'):
        identity = identity + '/'
    return identity


def getPapeRequestInfo(request):
    pape_req = pape.Request.fromOpenIDRequest(request)
    if pape_req is None:
        return 0, [], {}
    return pape_req.max_auth_age, pape_req.preferred_auth_policies,\
        pape_req.preferred_auth_level_types


def addSReg(request, response):
    sreg_req = sreg.SRegRequest.fromOpenIDRequest(request)
    sreg_data = get_auth_module().get_sreg()
    sreg_resp = sreg.SRegResponse.extractResponse(sreg_req, sreg_data)
    response.addExtension(sreg_resp)
    return sreg_resp.data


def addPape(request, response):
    auth_time = datetime.utcfromtimestamp(
        get_session()['last_auth_time']).strftime('%Y-%m-%dT%H:%M:%SZ')
    auth_policies = []
    auth_levels = {}
    auth_levels[pape.LEVELS_NIST] = 2

    if get_auth_module().used_multi_factor():
        auth_policies.append(pape.AUTH_MULTI_FACTOR)
        if get_auth_module().used_multi_factor_physical():
            auth_policies.append(pape.AUTH_MULTI_FACTOR_PHYSICAL)
            if get_auth_module().used_phishing_resistant():
                auth_policies.append(pape.AUTH_PHISHING_RESISTANT)
                auth_levels[pape.LEVELS_NIST] = 3
    else:
        auth_policies.append(pape.AUTH_NONE)

    pape_resp = pape.Response(
        auth_policies=auth_policies,
        auth_time=auth_time,
        auth_levels=auth_levels)
    response.addExtension(pape_resp)
    return auth_levels[pape.LEVELS_NIST]


def addTeams(request, response, groups):
    teams_req = teams.TeamsRequest.fromOpenIDRequest(request)
    if '_FAS_ALL_GROUPS_' in teams_req.requested and \
            app.config['FAS_HANDLE_GROUPS_MAGIC_VALUE']:
        # We will send all groups the user is a member of
        teams_req.requested = groups
    teams_resp = teams.TeamsResponse.extractResponse(teams_req, groups)
    if not response is None and teams_req.requested != []:
        response.addExtension(teams_resp)
    return teams_resp


def addCLAs(request, response, cla_uris):
    cla_req = cla.CLARequest.fromOpenIDRequest(request)
    if cla_req.requested == []:
        return
    cla_resp = cla.CLAResponse.extractResponse(cla_req, cla_uris)
    response.addExtension(cla_resp)
    return cla_resp.clas


def user_ask_trust_root(openid_request):
    if request.method == 'POST' and 'form_filled' in request.form:
        if not 'csrf_id' in get_session() \
                or not 'csrf_value' in request.form \
                or request.form['csrf_value'] != get_session()['csrf_id']:
            return 'CSRF Protection value invalid'
        if 'decided_allow' in request.form:
            addToSessionArray('TRUSTED_ROOTS', openid_request.trust_root)
        else:
            addToSessionArray('NON_TRUSTED_ROOTS', openid_request.trust_root)
        return redirect(request.url)
    get_session()['csrf_id'] = uuid().hex
    get_session().save()
    # Get which stuff we will send
    sreg_data = get_auth_module().get_sreg()
    sreg_req = sreg.SRegRequest.fromOpenIDRequest(openid_request)
    sreg_resp = sreg.SRegResponse.extractResponse(sreg_req, sreg_data)
    teams_resp = addTeams(openid_request, None, filter_cla_groups(get_auth_module().get_groups()))
    clas_req = cla.CLARequest.fromOpenIDRequest(openid_request)
    clas_resp = cla.CLAResponse.extractResponse(
        clas_req,
        get_cla_uris(get_auth_module().get_groups()))
    # Show form
    return render_template(
        'openid_user_ask_trust_root.html',
        action=complete_url_for('view_main'),
        trust_root=openid_request.trust_root,
        sreg_policy_url=sreg_req.policy_url or _('None provided'),
        sreg_data=sreg_resp.data,
        teams_provided=teams_resp.teams,
        cla_done=cla.CLA_URI_FEDORA_DONE in clas_resp.clas,
        csrf=get_session()['csrf_id'])


@app.route('/api/v1/', methods=['POST'])
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
    auth_result = get_auth_module().api_authenticate(values)
    if not auth_result:
        return {'success': False,
                'status': 403,
                'message': 'Authentication failed'
                }
    openid_response = openid_request.answer(
        True,
        identity=get_claimed_id(auth_result['username']),
        claimed_id=get_claimed_id(auth_result['username'])
    )
    # SReg
    sreg_req = sreg.SRegRequest.fromOpenIDRequest(openid_request)
    sreg_resp = sreg.SRegResponse.extractResponse(sreg_req, auth_result)
    openid_response.addExtension(sreg_resp)
    # Teams
    teams_req = teams.TeamsRequest.fromOpenIDRequest(openid_request)
    if teams_req.requested != []:
        groups = filter_cla_groups(auth_result['groups'])
        teams_resp = teams.TeamsResponse.extractResponse(teams_req,
                                                         groups)
        openid_response.addExtension(teams_resp)
    # CLA
    cla_req = cla.CLARequest.fromOpenIDRequest(openid_request)
    if cla_req.requested != []:
        cla_uris = get_cla_uris(auth_result['groups'])
        cla_resp = cla.CLAResponse.extractResponse(cla_req, cla_uris)
        openid_response.addExtension(cla_resp)
    # PAPE
    pape_resp = pape.Response(
        auth_policies=[],
        auth_time=datetime.utcfromtimestamp(time()).strftime(
                                        '%Y-%m-%dT%H:%M:%SZ'),
        auth_levels={pape.LEVELS_NIST: 2})
    openid_response.addExtension(pape_resp)
    # Return
    response_strings = get_server().signatory.sign(openid_response). \
        encodeToKVForm().split('\n')
    response = {}
    for resp in response_strings:
        if resp != '':
            resp = resp.split(':', 1)
            response['openid.%s' % resp[0]] = resp[1]
    return {'success': True,
            'response': response}


def view_openid_main():
    if 'openid.mode' in request.values:
        values = request.values
        get_session()['values'] = request.values
        get_session().save()
    else:
        if 'values' in get_session():
            values = get_session()['values']
        else:
            values = {}

    try:
        openid_request = get_server().decodeRequest(values)
    except server.ProtocolError, openid_error:
        return openid_respond(openid_error)

    if openid_request is None:
        return render_template(
            'index.html',
            yadis_url=complete_url_for('view_openid_yadis')
        ), 200, {'X-XRDS-Location': complete_url_for('view_openid_yadis')}
    elif openid_request.mode in ['checkid_immediate', 'checkid_setup']:
        authed = isAuthorized(openid_request)
        if authed == AUTH_OK:
            openid_response = openid_request.answer(
                True,
                identity=get_claimed_id(
                    get_auth_module().get_username()
                ),
                claimed_id=get_claimed_id(get_auth_module().get_username())
            )
            addSReg(openid_request, openid_response)
            teams_info = addTeams(
                openid_request,
                openid_response,
                filter_cla_groups(get_auth_module().get_groups()))
            addCLAs(
                openid_request,
                openid_response,
                get_cla_uris(get_auth_module().get_groups()))
            auth_level = addPape(openid_request, openid_response)
            log_info('Success', {
                'claimed_id': get_claimed_id(get_auth_module().get_username()),
                'trust_root': openid_request.trust_root,
                'security_level': auth_level,
                'message': 'The user succesfully claimed the identity'})
            log_debug('Info', {'teams': teams_info.teams})
            return openid_respond(openid_response)
        elif authed == AUTH_TRUST_ROOT_ASK:
            # User needs to confirm trust root
            return user_ask_trust_root(openid_request)
        elif authed == AUTH_TRUST_ROOT_NOT_OK:
            log_info('Info', {
                'trust_root': openid_request.trust_root,
                'message': 'User chose not to trust trust_root'})
            return openid_respond(openid_request.answer(False))
        elif authed == AUTH_TRUST_ROOT_CONFIG_NOT_OK:
            log_info('Info', {
                'trust_root': openid_request.trust_root,
                'message': 'Configuration blacklisted this trust_root'})
            return openid_respond(openid_request.answer(False))
        elif openid_request.immediate:
            log_warning('Error', {
                'trust_root': openid_request.trust_root,
                'message': 'Trust root demanded checkid_immediate'})
            return openid_respond(openid_request.answer(False))
        elif authed == AUTH_TIMEOUT:
            get_session()['timeout'] = True
            get_session()['next'] = request.base_url
            get_session().save()
            return get_auth_module().start_authentication()
        elif authed == AUTH_NOT_LOGGED_IN:
            get_session()['next'] = request.base_url
            get_session()['trust_root'] = openid_request.trust_root
            get_session().save()
            return get_auth_module().start_authentication()
        else:
            log_error('Failure', {
                'username': get_auth_module().get_username(),
                'attempted_claimed_id': openid_request.identity,
                'trust_root': openid_request.trust_root,
                'message':
                'The user tried to claim an ID that is not theirs'})
            return 'This is not your ID! If it is, please contact the ' \
                'administrators at admin@fedoraproject.org. Be sure to ' \
                'mention your session ID: %(logid)s' % {
                    'logid': get_session()['log_id']}
    else:
        return openid_respond(get_server().handleRequest(openid_request))


def isAuthorized(openid_request):
    pape_req_time, pape_auth_policies, pape_auth_level_types = \
        getPapeRequestInfo(openid_request)

    if not get_auth_module().logged_in():
        return AUTH_NOT_LOGGED_IN
    elif (pape_req_time) and (pape_req_time != 0) and (
            get_session()['last_auth_time'] < (time() - pape_req_time)):
        return AUTH_TIMEOUT
    elif (app.config['OPENID_MAX_AUTH_TIME'] != 0) and (
            get_session()['last_auth_time'] < (time() - (
            app.config['OPENID_MAX_AUTH_TIME'] * 60))):
        return AUTH_TIMEOUT
    # Add checks if yubikey is required by application
    elif (not openid_request.idSelect()) and (
            openid_request.identity != get_claimed_id(
                get_auth_module().get_username())):
        return AUTH_INCORRECT_IDENTITY
    elif openid_request.trust_root in app.config['OPENID_TRUSTED_ROOTS']:
        return AUTH_OK
    elif openid_request.trust_root in app.config['OPENID_NON_TRUSTED_ROOTS']:
        return AUTH_TRUST_ROOT_CONFIG_NOT_OK
    elif openid_request.trust_root in getSessionValue('TRUSTED_ROOTS', []):
        return AUTH_OK
    elif openid_request.trust_root in getSessionValue('NON_TRUSTED_ROOTS', []):
        return AUTH_TRUST_ROOT_NOT_OK
    else:
        # The user still needs to determine if he/she allows this trust root
        return AUTH_TRUST_ROOT_ASK


@app.route('/id/<username>/')
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


@app.route('/yadis/<username>.xrds')
def view_openid_yadis_id(username):
    return no_cache(Response(render_template('openid_yadis_user.xrds',
                    claimed_id=get_claimed_id(username)),
                    mimetype='application/xrds+xml'))


@app.route('/yadis.xrds')
def view_openid_yadis():
    return no_cache(Response(render_template('openid_yadis.xrds'),
                    mimetype='application/xrds+xml'))


def openid_respond(openid_response):
    get_session()['TRUSTED_ROOTS'] = []
    get_session()['NON_TRUSTED_ROOTS'] = []
    get_session().save()
    if 'values' in get_session():
        get_session()['values'] = None
        get_session().save()
    try:
        webresponse = get_server().encodeResponse(openid_response)
        return (webresponse.body, webresponse.code, webresponse.headers)
    except server.EncodingError, why:
        headers = {'Content-type': 'text/plain; charset=UTF-8'}
        return why.response.encodeToKVForm(), 400, headers
