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
from flask import request, render_template
from fedoauth.auth.base import Auth_Base, \
    UnauthorizedError, UnknownAttributeError, NotRequestedAttributeError
from itsdangerous import TimedSerializer
import time


import logging
logger = logging.getLogger(__name__)


class Auth_webSilvia(Auth_Base):
    def __init__(self, config):
        self.signer = TimedSerializer(config['shared_secret'])
        super(Auth_webSilvia, self).__init__(config)

    # This functions returns which credentials we need to retrieve
    #  to get all of the requested_attributes
    def get_credentials(self, requested_attributes):
        credentials_to_request = self.config['always_retrieve']

        if '/' in self.config['username_mapping']:
            credential, _ = self.config['username_mapping'].split('/', 1)
            credentials_to_request.append(credential)

        for requested_attribute in requested_attributes:
            if requested_attribute in self.config['attribute_mapping'].keys():
                if '/' in self.config['attribute_mapping'][requested_attribute]:
                    credential, _ = self.config['attribute_mapping'][requested_attribute].split('/', 1)
                    credentials_to_request.append(credential)

        credentials_request = {}
        for credential_to_request in credentials_to_request:
            if credential_to_request in self.config['known_credentials']:
                credentials_request[credential_to_request] = self.config['known_credentials'][credential_to_request]
            else:
                # We do not know the paths for this credential...
                logger.error('Credential was mapped to, but could not be found: %s', credential_to_request)

        return credentials_request

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
        if request.method == 'POST':
            # We are returning from webSilvia!
            result = request.form['result']
            result = self.signer.loads(result)

            user = {}
            needed_credentials = self.config['required_credentials']
            for credential in result['credentials']:
                if result['credentials'][credential]['status'] == 'OK':
                    if result['credentials'][credential]['expiry'] >= time.time():
                        if credential in needed_credentials:
                            needed_credentials.remove(credential)
                        user[credential] = result['credentials'][credential]['attributes']
                    else:
                        # Attribute no longer valid
                        logger.info('Credential expired: %s', result['credentials'][credential])
                else:
                    # Attribute status != OK
                    logger.info('Credential not status=OK: %s', result['credentials'][credential])

            if len(needed_credentials) > 0:
                return False

            self.save_success(user)
            return True
        else:
            # Build the request for webSilvia
            websilvia_request = {'return_url': '%s?transaction=%s' % (form_url, request.transaction_id),
                                'token': request.transaction_id,
                                'nonce': time.time(),
                                'credentials': self.get_credentials(requested_attributes)}
            websilvia_request = self.signer.dumps(websilvia_request)

            return render_template('webSilvia.html',
                                   request=websilvia_request,
                                   websilvia_url=self.config['websilvia_url'])

    def follow_mapping(self, mapping, user):
        if '/' not in mapping:
            return mapping
        else:
            credential, attribute = mapping.split('/', 1)
            if credential in self._user.keys():
                if attribute in self._user[credential]:
                    return self._user[credential][attribute]
                else:
                    raise NotRequestedAttributeError()
            else:
                raise NotRequestedAttributeError()

    def get_username(self):
        if not self.logged_in():
            raise UnauthorizedError
        return self.follow_mapping(self.config['username_mapping'],
                                   self._user)

    def get_attribute(self, attribute):
        if not self.logged_in():
            raise UnauthorizedError
        attribute = attribute.__str__()
        if attribute in self.config['attribute_mapping']:
            return self.follow_mapping(self.config['attribute_mapping'][attribute], self._user)
        else:
            raise UnknownAttributeError()

    def get_groups(self):
        return []

    def get_clas(self):
        return []

    def used_multi_factor(self):
        return True

    def used_multi_factor_physical(self):
        return True

    def used_phishing_resistant(self):
        return False
