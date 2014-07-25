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
from enum import Enum
from datetime import datetime, timedelta
import json
from uuid import uuid4
from flask import request, render_template
import logging

from fedoauth.model import Remembered


logger = logging.getLogger(__name__)

StandardAttributes = Enum('nickname',
                          'email',
                          'fullname',
                          'dob',
                          'gender',
                          'postalcode',
                          'country',
                          'language',
                          'timezone',
                          'firstname',
                          'lastname',
                          'gpg_keyid',
                          'ssh_key')


class UnauthorizedError(StandardError):
    pass


class UnknownAttributeError(KeyError):
    pass


class NotRequestedAttributeError(KeyError):
    pass


class Auth_Base(object):
    def __init__(self, config):
        self.config = config

    def __getattr__(self, name):
        if name == 'full_name':
            module = self.__class__.__module__
            if module is None:
                return self.__class__.__name__
            return module + '.' + self.__class__.__name__
        elif name == '_user':
            if not self.logged_in():
                raise UnauthorizedError
            return request.transaction['%s_user' % self.full_name]
        else:
            return super(object, self).__getattribute__(name)

    def get_select_info(self, url):
        return {'text': self.__class__.__name__,
                'image': self.config['select_image'],
                'url': url}

    def logged_in(self):
        if ('%s_loggedin' % self.full_name) in request.transaction and \
                request.transaction['%s_loggedin' % self.full_name] is True:
            return True

        # Check if the user still has an active auth session
        if ('%s_auth_ses' % self.full_name) in request.cookies:
            # Seems so, let's check if it is still valid
            # We don't really care about the reauth_timeout when the cookie
            #  was set. All that matters is the setting as of this request
            authsesid = request.cookies['%s_auth_ses' % self.full_name]
            logger.debug('Got an authsesid: %s' % authsesid)
            try:
                authsesid = request.signer.unsign(authsesid,
                                                  self.config['reauth_timeout']
                                                  * 60)
                logger.debug('Correctly verified authsesid')
                remembered = Remembered.getremembered('authses',
                                                      self.full_name,
                                                      authsesid)
                logger.debug('Authsesid remembered: %s' % remembered)
                if remembered is not None:
                    # Yay, we got a still valid auth session. Let us restore
                    #  the user info and set the loggedin information
                    # We should not re-store the auth cookie, so that it keeps
                    #  the old expiry date/time
                    self.save_success(json.loads(remembered.data), False)
                    return True
            except:
                # If anything fails in retrieving session, we don't want
                #  anything to do with it anymore
                # But let's clear up the previous session so we don't spend
                #  every request checking if it happens to be valid this time
                request.set_cookie('%s_auth_ses' % self.full_name,
                                   None,
                                   expires=0)
                pass

        return False

    # This is used to determine if this auth provider is willing to sign for
    #  the specified email domain
    # This is used to limit the list of displayed auth providers to the
    #  providers willing to sign for the email address provided by the user
    def allows_email_auth_domain(self, domain):
        return domain in self.config['email_auth_domains']

    def willing_to_sign_for_email(self, email):
        if not self.logged_in():
            logger.info('User not logged in')
            raise UnauthorizedError
        if '@' not in email:
            logger.info('Invalid email: %s' % email)
            raise ValueError('No email address!')
        (user, domain) = email.split('@')
        if not self.allows_email_auth_domain(domain):
            logger.info('Domain not allowed')
            return False
        return self.email_is_valid_for_user(user, domain)

    # This tells us if the email domain is valid for this user
    # By default, we will sign for a user with any domain we are configured to
    #  sign for, if you want to restrict this, the auth provider should be
    #  able to return the user's full domain name
    def email_is_valid_for_user(self, user, domain):
        return user == self.get_username()

    # Do the actual authentication
    # Whatever you do, make sure to pass request.transaction_id either in GET
    #  or POST in the field 'transaction'.
    # The requested_attributes can be used in authentication modules that need
    #  to know up-front which attributes are going to be requested. Any
    #  attributes not requested here MAY raise a NotRequestedAttributeError on
    #  attempt to retrieval, but it's also perfectly valid for the auth module
    #  to just return the value if it can retrieve it.
    # Return True when authentication was successful
    # Return False when authentication was cancelled
    # Anything else will be returned to Flask as view result
    def authenticate(self, login_target, form_url, requested_attributes=[]):
        raise NotImplementedError()

    # This function is used for authentication to the API
    # This can return True or False, in which case default errors (or success)
    #  will be sent
    # It can also return a dict that will be extended with the transaction id
    #  so it is possible to implement multi-stage authentication
    def authenticate_api(self, values):
        raise NotImplementedError()

    # Can be used to easily save success results to the transaction
    def save_success(self, user, remember=True):
        logger.debug('Saving success: %s' % user)
        request.transaction['%s_loggedin' % self.full_name] = True
        request.transaction['%s_user' % self.full_name] = user
        request.transaction['%s_last_login' % self.full_name] = datetime.now()
        if remember:
            logger.debug('Remembering the following: %s' % user)
            logger.debug('Remembering the following: %s' % json.dumps(user))
            # We should remember the auth in a Remembered object and a reauth
            #  cookie
            authsesid = uuid4().hex
            signed_authsesid = request.signer.sign(authsesid)
            logger.debug('Signed authsesid: %s' % signed_authsesid)
            Remembered.remember('authses',
                                timedelta(minutes=self.config['reauth_timeout']),
                                json.dumps(user),
                                self.full_name,
                                authsesid)
            request.set_cookie('%s_auth_ses' % self.full_name,
                               signed_authsesid)
            logger.debug('Cookie set')

        logger.debug('Login complete')
        request.save_transaction()

    def get_username(self):
        raise NotImplementedError()

    # Return UnauthorizedError if not logged in
    # Return UnknownAttributeError if unknown attribute
    def get_attribute(self, attribute):
        raise NotImplementedError()

    # Accepts a list of attributes to retrieve
    # Return a dict with all valid attributes and their values
    def get_attributes(self, attributes):
        # Can be overriden if the underlying module has an efficient way to get
        # multiple attributes at the same time
        # Otherwise just tries to get attributes one at a time
        values = {}
        for attribute in attributes:
            try:
                values[attribute.__str__()] = self.get_attribute(attribute)
            except:
                pass
        return values

    def get_groups(self):
        raise NotImplementedError()

    def get_clas(self):
        raise NotImplementedError()

    def last_loggedin(self):
        return request.transaction['%s_last_login' % self.full_name]

    def used_multi_factor(self):
        raise NotImplementedError()

    def used_multi_factor_physical(self):
        raise NotImplementedError()

    def used_phishing_resistant(self):
        raise NotImplementedError()


class Auth_UsernamePasswordBase(Auth_Base):
    # Do the actual authentication
    # Whatever you do, make sure to pass request.transaction_id either in GET
    #  or POST in the field 'transaction'.
    # The requested_attributes can be used in authentication modules that need
    #  to know up-front which attributes are going to be requested. Any
    #  attributes not requested here MAY raise a NotRequestedAttributeError on
    #  attempt to retrieval, but it's also perfectly valid for the auth module
    #  to just return the value if it can retrieve it.
    # Return True when authentication was successful
    # Return False when authentication was cancelled
    # Anything else will be returned to Flask as view result
    # The default is user/password-based authentication calling check_user_pass
    def authenticate(self, login_target, form_url, requested_attributes=[]):
        error = None
        username = ''
        forced_username = False
        if 'forced_username' in request.transaction:
            forced_username = True
            username = request.transaction['forced_username']
        if request.method == 'POST':
            if 'cancel' in request.form:
                logger.debug('Cancelling')
                return False
            if ('username' not in request.form and not forced_username) or \
                    'password' not in request.form:
                error = 'Invalid form submitted'
            else:
                if not forced_username:
                    username = request.form['username']
                valid = False
                try:
                    valid = self.check_user_pass(username,
                                                 request.form['password'])
                    self.save_success(valid)
                except Exception, ex:
                    logger.info('Auth error: %s' % ex)
                    pass
                if valid is False:
                    error = 'Invalid username or password'
                else:
                    return True
        return render_template('login_form.html',
                               username=username,
                               forced_username=forced_username,
                               form_url=form_url,
                               login_target=login_target,
                               transaction=request.transaction_id,
                               error=error)

    # This function is used for authentication to the API
    # This can return True or False, in which case default errors (or success)
    #  will be sent
    # It can also return a dict that will be extended with the transaction id
    #  so it is possible to implement multi-stage authentication
    def authenticate_api(self, values):
        valid = self.check_user_pass(values['username'], values['password'])
        if valid is not False:
            self.save_success(valid)
            return True
        return False

    # The function that returns whether or not a username/password was valid
    # This should also set the current user info in request.transaction
    def check_user_pass(self, username, password):
        raise NotImplementedError()

    def used_multi_factor(self):
        return False

    def used_multi_factor_physical(self):
        return False

    def used_phishing_resistant(self):
        return False
