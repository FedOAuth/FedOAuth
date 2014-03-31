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
try:
    from flask import _app_ctx_stack as stack
except ImportError:
    from flask import _request_ctx_stack as stack

from fedora.client.fasproxy import FasProxyClient

import openid_cla.cla as cla

import logging

from fedoauth.auth.base import Auth_UsernamePasswordBase, UnauthorizedError, \
    UnknownAttributeError, StandardAttributes


logger = logging.getLogger(__name__)


CLA_GROUPS = {'cla_click': cla.CLA_URI_FEDORA_CLICK,
              'cla_dell': cla.CLA_URI_FEDORA_DELL,
              'cla_done': cla.CLA_URI_FEDORA_DONE,
              'cla_fedora': cla.CLA_URI_FEDORA_FEDORA,
              'cla_fpca': cla.CLA_URI_FEDORA_FPCA,
              'cla_ibm': cla.CLA_URI_FEDORA_IBM,
              'cla_intel': cla.CLA_URI_FEDORA_INTEL,
              'cla_redhat': cla.CLA_URI_FEDORA_REDHAT
              }


class Auth_FAS(Auth_UsernamePasswordBase):
    # This hackaround is because this is per request
    def _get_fasclient(self):
        ctx = stack.top
        if not hasattr(ctx, 'fasclient'):
            ctx.fasclient = FasProxyClient(
                base_url=self.config['base_url'],
                useragent=self.config['user_agent'],
                insecure=not self.config['check_cert'])
        return ctx.fasclient

    def check_user_pass(self, username, password):
        session_id, data = self._get_fasclient().login(username, password)
        return data.user

    def get_username(self):
        if not self.logged_in():
            raise UnauthorizedError
        return self._user['username']

    def get_attribute(self, attribute):
        if not self.logged_in():
            raise UnauthorizedError
        if attribute == StandardAttributes.nickname:
            return self._user['username']
        elif attribute == StandardAttributes.email:
            return self._user['email']
        elif attribute == StandardAttributes.fullname:
            return self._user['human_name']
        elif attribute == StandardAttributes.timezone:
            return self._user['timezone']
        elif attribute == StandardAttributes.country:
            return self._user['country_code']
        elif attribute == StandardAttributes.gpg_keyid:
            return self._user['gpg_keyid']
        elif attribute == StandardAttributes.ssh_key:
            return self._user['ssh_key']
        raise UnknownAttributeError

    def get_groups(self):
        groups = self._user['groups']
        return [group for group in groups if group not in CLA_GROUPS.keys()]

    def get_clas(self):
        groups = self._user['groups']
        return [CLA_GROUPS[group]
                for group in groups if group in CLA_GROUPS.keys()]

    def used_multi_factor(self):
        return False

    def used_multi_factor_physical(self):
        return False

    def used_phishing_resistant(self):
        return False
