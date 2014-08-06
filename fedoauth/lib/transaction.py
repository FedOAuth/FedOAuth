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

import logging
import flask
from itsdangerous import TimestampSigner

from fedoauth import APP, dbsession, get_loaded_auth_modules
import fedoauth.model
import fedoauth.utils


logger = logging.getLogger(__name__)


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
        elif name == 'user':
            return self._get_user()
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
            fedoauth.model.Transaction.query.filter_by(key=self._transaction.key).delete()
            self._transaction = None

    def delete_transaction_after_request(self):
        @fedoauth.utils.after_this_request
        def delete_transaction_after_request_inner(response):
            if self._transaction:
                response.set_cookie('tr%s' % self._transaction.key, expires=0)
                self.delete_transaction()

    def set_cookie(self, name, value, **kwargs):
        @fedoauth.utils.after_this_request
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
            @fedoauth.utils.after_this_request
            def persist_transaction(response):
                response.set_cookie(
                    'persistent_transaction',
                    self.signer.sign(self._transaction.key),
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
                    trid = self.signer.unsign(value, max_age=30)
                    logger.debug('persistent trid accepted')
                except Exception, ex:
                    @fedoauth.utils.after_this_request
                    def clear_persistent_transaction(response):
                        response.set_cookie('persistent_transaction', expires=0)
                    logger.warning('Error getting persistent transaction: %s',
                                   ex)
            transaction = fedoauth.model.Transaction.query.filter_by(key=trid).first()
            logger.debug('Attempt to get current transaction: %s' %
                         transaction)
            if transaction:
                # Verify this user has the correct cookie
                trans_verify = flask.request.cookies.get('tr%s' %
                                                         transaction.key)
                if trans_verify == transaction.values['check']:
                    self._transaction = transaction
                else:
                    logger.error('Transaction stealing attempted! Transaction values: %s, Cookies: %s', transaction.values, flask.request.cookies)
        if not self._transaction:
            self._new_transaction = True
            self._transaction = fedoauth.model.Transaction()
            dbsession.add(self._transaction)
            dbsession.commit()

            logger.debug('Created new transaction')

        if retrieved_transaction:
            # Refresh cookie
            @fedoauth.utils.after_this_request
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
        for auth_module in get_loaded_auth_modules():
            if auth_module.logged_in():
                return auth_module
