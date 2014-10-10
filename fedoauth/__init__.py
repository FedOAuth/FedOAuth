#!/usr/bin/python
# Since this is always the first query executed in a new
#  request, this is the one that always get the mess thrown
#  in its face. Let's just make sure that any previous
#  requests can not break this one.

#-*- coding: UTF-8 -*-
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

## These two lines are needed to run on EL6
__requires__ = ['SQLAlchemy >= 0.7', 'jinja2 >= 2.4']
import pkg_resources

# Imports
import flask
import jinja2

import logging
import logging.config

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.exc import InvalidRequestError

import sys
from itsdangerous import TimestampSigner


# Create the application
APP = flask.Flask(__name__)


APP.config.from_envvar('FEDOAUTH_CONFIG')

# Make sure the configuration is sane
if APP.config['GLOBAL']['url_root'].endswith('/'):
    print 'Error: Make sure url_root does NOT end with a trailing slash'
    sys.exit(1)
if APP.config['GLOBAL']['secret_key'] == 'setme':
    print 'Error: Please configure a secret key'
    sys.exit(1)

signer = TimestampSigner(APP.config['GLOBAL']['secret_key'])

logging.config.fileConfig(APP.config['GLOBAL']['logging_config_location'])


logger = logging.getLogger(__name__)


# Set up SQLAlchemy
# DEPRECATED: the global SQLALCHEMY_DATABASE_URI is deprecated, but should stay supported during the 3.0.X series
db_url = None
db_debug = APP.config['GLOBAL'].get('database_debug', False)
db_url = APP.config['GLOBAL']['database_url']
dbengine = create_engine(db_url, echo=db_debug, pool_recycle=3600)
dbsession = scoped_session(sessionmaker(bind=dbengine))

import fedoauth.utils as utils
if APP.config['GLOBAL']['reverse_proxied']:
    APP.wsgi_app = utils.ReverseProxied(APP.wsgi_app)


# Transaction stuff
# Please prefix module-specific keys with __name__ to prevent key collisions
import fedoauth.model as model


class TransactionRequest(flask.Request):
    _transaction = None
    _new_transaction = False
    _signer = None

    def __getattr__(self, name):
        if name == 'transaction':
            return self._get_transaction().values
        elif name == 'transaction_id':
            return self._get_transaction().key
        elif name == 'transaction_new':
            self._get_transaction()
            return self._new_transaction
        elif name == 'auth_module':
            return self._get_auth_module()
        elif name == 'signer':
            return self._get_signer()
        else:
            return super(flask.Request, self).__getattribute__(name)

    def _get_signer(self):
        if self._signer is None:
            # We are using the timestampsigner because we want to be always
            #  needing to think about expiry of the signatures
            self._signer = TimestampSigner(APP.config['GLOBAL']['secret_key'])
        return self._signer

    def save_transaction(self):
        if self._transaction:
            dbsession.add(self._transaction)
            dbsession.commit()

    def delete_transaction(self):
        if self._transaction:
            logger.debug('Deleting transaction %s', self._transaction.key)
            model.Transaction.query.filter_by(key=self._transaction.key).delete()
            self._transaction = None

    def delete_transaction_after_request(self):
        @utils.after_this_request
        def delete_transaction_after_request_inner(response):
            if self._transaction:
                response.set_cookie('tr%s' % self._transaction.key, expires=0)
                self.delete_transaction()

    def set_cookie(self, name, value, **kwargs):
        @utils.after_this_request
        def set_cookie(response):
            try:
                response.set_cookie(name,
                                    value,
                                    **kwargs)
            except:
                if value is None:
                    try:
                        response.set_cookie(name,
                                            '',
                                            **kwargs)
                    except:
                        logger.error('Unable to write cookie %s=%s', name, value)
                else:
                    logger.error('Unable to write non-empty cookie %s=%s', name, value)

    # Persistent transactions are used when the transaction should be retained
    # in a cookie for a VERY short amount of time (30 seconds).
    # This is for example required in persona
    # Please try to avoid using this if it's not required, and make sure to
    # delete the transaction if you no longer require it, as it breaks
    # multi-tab operation
    def persist_transaction(self):
        if self._transaction:
            @utils.after_this_request
            def persist_transaction(response):
                response.set_cookie(
                    'persistent_transaction',
                    signer.sign(self._transaction.key),
                    httponly=True,
                    max_age=60,
                    secure=APP.config['GLOBAL']['cookies_secure'])

    def _get_transaction(self):
        retrieved_transaction = self._transaction is None
        if not self._transaction:
            trid = None
            if 'transaction' in self.form:
                logger.debug('trid in form: %s', self.form['transaction'])
                trid = self.form['transaction']
            elif 'transaction' in self.args:
                logger.debug('trid in query: %s', self.args['transaction'])
                trid = self.args['transaction']
            elif 'persistent_transaction' in flask.request.cookies:
                value = flask.request.cookies.get('persistent_transaction')
                try:
                    logger.debug('trid in persistent_transaction: %s', value)
                    # Here is the value that decides how long a persistent
                    # is valid. TWEAK THIS IN CASE OF ISSUES
                    trid = signer.unsign(value, max_age=30)
                    logger.debug('persistent trid accepted')
                except Exception, ex:
                    @utils.after_this_request
                    def clear_persistent_transaction(response):
                        response.set_cookie('persistent_transaction', expires=0)
                    logger.warning('Error getting persistent transaction: %s',
                                   ex)
            try:
                transaction = model.Transaction.query.filter_by(key=trid).first()
            except InvalidRequestError:
                # This happens sometimes if the last request hit an error
                # Since this is always the first query executed in a new
                #  request, this is the one that always get the mess thrown
                #  in its face. Let's just make sure that any previous
                #  requests can not break this one.
                dbsession.rollback()
                transaction = model.Transaction.query.filter_by(key=trid).first()
            logger.debug('Attempt to get current transaction: %s' %
                         transaction)
            if transaction:
                # Verify this user has the correct cookie
                trans_verify = flask.request.cookies.get('tr%s' %
                                                         transaction.key)
                if trans_verify == transaction.values['check']:
                    self._transaction = transaction
                else:
                    logger.info('Transaction stealing attempted! Transaction values: %s, Cookies: %s', transaction.values, flask.request.cookies)
        if not self._transaction:
            self._new_transaction = True
            self._transaction = model.Transaction()
            dbsession.add(self._transaction)
            dbsession.commit()

            logger.debug('Created new transaction')

        if retrieved_transaction:
            # Refresh cookie
            @utils.after_this_request
            def set_transaction_cookie(response):
                # If we deleted the transaction, of course we shouldn't reset the cookie
                if self._transaction:
                    response.set_cookie(
                        'tr%s' % self._transaction.key,
                        self._transaction.values['check'],
                        httponly=True,
                        max_age=APP.config['GLOBAL']['transactions_timeout'] * 60,
                        secure=APP.config['GLOBAL']['cookies_secure'])
        return self._transaction

    def _get_auth_module(self):
        global loaded_auth_modules
        for auth_module in loaded_auth_modules:
            if auth_module.logged_in():
                return auth_module

APP.request_class = TransactionRequest

# Use the templates
# First we test the core templates directory
#  (contains stuff that users won't see)
# Then we use the configured template directory
templ_loaders = []
templ_loaders.append(APP.jinja_loader)
templ_loaders.append(jinja2.FileSystemLoader('%s' % APP.config['GLOBAL']['template_dir']))
templ_loaders.append(jinja2.FileSystemLoader('%s' % APP.config['GLOBAL']['global_template_dir']))

APP.jinja_loader = jinja2.ChoiceLoader(templ_loaders)

APP.jinja_env.globals['url_root'] = APP.config['GLOBAL']['url_root']
APP.jinja_env.globals['static_content_root'] = APP.config['GLOBAL']['static_content_root']
try:
    APP.jinja_env.globals['version'] = pkg_resources.get_distribution('fedoauth').version
except:
    APP.jinja_env.globals['version'] = 'Unknown. Development?'


app_version = 'Development version'
try:
    app_version = pkg_resources.get_distribution("fedoauth").version
except:
    pass
APP.jinja_env.globals['VERSION'] = app_version


# Import the other stuff (this needs to be done AFTER setting db connection)
# Import enabled auth methods
loaded_auth_modules = []
listed_auth_modules = []


def get_auth_module_by_name(name):
    global loaded_auth_modules
    for loaded_auth_module in loaded_auth_modules:
        if name == loaded_auth_module._internal_name:
            return loaded_auth_module

def get_listed_auth_modules(email_domain=None):
    global listed_auth_modules
    toreturn = []
    for module in listed_auth_modules:
        if email_domain is None or \
                get_auth_module_by_name(module).allows_email_auth_domain(email_domain):
            toreturn.append(module)
    return toreturn

# Initialize all the modules specified in AUTH_MODULES_ENABLED
for auth_module_name in APP.config['AUTH_MODULE_CONFIGURATION']:
    if APP.config['AUTH_MODULE_CONFIGURATION'][auth_module_name]['enabled']:
        auth_module_name_split = auth_module_name.rsplit('.', 1)
        # This fromlist= is because otherwise it will only import the module
        auth_module = __import__(auth_module_name_split[0],
                                 fromlist=[auth_module_name_split[1]])
        auth_module = getattr(auth_module, auth_module_name_split[1])
        auth_module = auth_module(APP.config['AUTH_MODULE_CONFIGURATION'][auth_module_name])
        auth_module._internal_name = auth_module_name
        loaded_auth_modules.append(auth_module)
        if 'listed' in APP.config['AUTH_MODULE_CONFIGURATION'][auth_module_name] and \
                APP.config['AUTH_MODULE_CONFIGURATION'][auth_module_name]['listed']:
            listed_auth_modules.append(auth_module_name)


import views

for provider in APP.config['AUTH_PROVIDER_CONFIGURATION']:
    if APP.config['AUTH_PROVIDER_CONFIGURATION'][provider]['enabled']:
        provider_module = __import__(provider)
