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
from logging import getLogger
from flask import request, redirect, render_template
import json

from fedoauth import APP, get_auth_module_by_name, get_listed_auth_modules
from fedoauth.utils import complete_url_for, require_login

logger = getLogger(__name__)


@APP.route('/robots.txt')
def view_robots():
    # Search robots have nothing to search in FedOAuth
    return 'User-Agent: *\nDisallow: /'


def error_to_string(err):
    if err == 'no-transaction':
        return 'Transaction missing'
    else:
        logger.debug('Unknown error code requested: %s', err)
        return None


@APP.route('/', methods=['GET'])
def view_main():
    error = None
    if 'err' in request.args:
        error = error_to_string(request.args['err'])
    yadis_url = ''
    if 'fedoauth.provider.openid' in APP.config['AUTH_PROVIDER_CONFIGURATION'] and \
            APP.config['AUTH_PROVIDER_CONFIGURATION']['fedoauth.provider.openid']['enabled']:
        yadis_url = complete_url_for('view_openid_yadis')
    return render_template(
        'index.html',
        yadis_url=yadis_url,
        error=error
    ), 200, {'X-XRDS-Location': yadis_url}


@APP.route('/logout/')
def view_logout():
    cookies = json.dumps(request.cookies)
    for cookie in request.cookies:
        request.set_cookie(cookie, None, expires=0)

    return 'The following cookies have been removed: %s. YUM' % cookies


if APP.config['GLOBAL']['enable_test_endpoint']:
    @APP.route('/test/')
    def view_test():
        require_login('test', 'view_test', 'view_test_failure')

        # Please note that you should NEVER use this
        # This is used here only because this is a test.
        # _user() might not exist for a lot of authentication modules
        return 'Success: %s' % request.auth_module._user


    @APP.route('/test/failure/')
    def view_test_failure():
        return 'Failure!'


@APP.route('/authenticate/<module>/', methods=['GET', 'POST'])
def view_authenticate_module(module):
    if not 'success_forward' in request.transaction or \
            not 'failure_forward' in request.transaction or \
            not 'login_target' in request.transaction:
        logger.info('Invalid request without success or failure urls or login target in the transaction')
        logger.debug('Transaction: %s', request.transaction)
        return redirect(complete_url_for('view_main'))

    url_success = complete_url_for(request.transaction['success_forward'],
                                   transaction=request.transaction_id)

    email_auth_domain = None
    if 'email_auth_domain' in request.transaction:
        email_auth_domain = request.transaction['email_auth_domain']

    auth_module = get_auth_module_by_name(module)
    if not auth_module:
        logger.warning('Selected module %s, but no longer available', module)
        return redirect(complete_url_for('view_authenticate', transaction=request.transaction_id))
    result = auth_module.authenticate(request.transaction['login_target'],
                                      complete_url_for('view_authenticate_module',
                                                       module=module),
                                      requested_attributes=request.transaction['requested_attributes'])
    if result == True:
        logger.debug('Was already logged on')
        return redirect(url_success)
    elif result == False:
        logger.debug('Authentication module cancelled')
        return redirect(complete_url_for('view_authenticate', transaction=request.transaction_id, cancelmodule=True))
    else:
        # Otherwise it's an flask result
        return result


@APP.route('/authenticate/')
def view_authenticate():
    own_url = complete_url_for('view_authenticate', transaction=request.transaction_id)
    email_auth_domain = None
    if 'email_auth_domain' in request.transaction:
        email_auth_domain = request.transaction['email_auth_domain']
    listed_auth_modules = get_listed_auth_modules(email_auth_domain)

    if not 'success_forward' in request.transaction or not 'failure_forward' in request.transaction or not 'login_target' in request.transaction:
        logger.info('Invalid request without success or failure urls or login target in the transaction')
        logger.debug('Transaction: %s', request.transaction)
        return redirect(complete_url_for('view_main'))

    url_success = complete_url_for(request.transaction['success_forward'], transaction=request.transaction_id)
    url_failure = complete_url_for(request.transaction['failure_forward'], transaction=request.transaction_id)

    if request.auth_module:
        if 'aready_authenticated' in request.transaction and \
                request.transaction['already_authenticated']:
            return 'ERROR: You are already authenticated, but still forwarded to authentication system'
        request.transaction['already_authenticated'] = True
        request.save_transaction()
        logger.debug('Was redirected to authenticate while already authenticated')
        return redirect(url_success)
    elif len(listed_auth_modules) == 1:
        # Only one module selectable. Select and redirect
        if 'cancelmodule' in request.args:
            logger.debug('Authentication cancelled')
            return redirect(url_failure)

        logger.debug('Automatically selecting module %s', listed_auth_modules[0])
        return redirect(complete_url_for('view_authenticate_module', module=listed_auth_modules[0], transaction=request.transaction_id))
    elif len(listed_auth_modules) == 0:
        if 'cancel' in request.args:
            logger.debug('Authentication cancelled')
            return redirect(url_failure)
        else:
            logger.debug('No listable authentication modules')
            return render_template('not_authenticated.html'), 401
    else:
        # Cancelled from selection screen
        if 'cancel' in request.args:
            logger.debug('Authentication cancelled')
            return redirect(url_failure)
        else:
            # Show selection form.
            modules = []
            for module in listed_auth_modules:
                url = complete_url_for('view_authenticate_module',
                                       module=module,
                                       transaction=request.transaction_id)
                modules.append(get_auth_module_by_name(module).get_select_info(url))

            return render_template('select_module.html',
                                   modules=modules,
                                   cancel_url=complete_url_for('view_authenticate',
                                                               transaction=request.transaction_id,
                                                               cancel=True)), 200
