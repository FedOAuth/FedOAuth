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
# Needed because we need the system package
from __future__ import absolute_import

import ldap

import logging

from fedoauth.auth.base import Auth_UsernamePasswordBase, UnauthorizedError, \
    UnknownAttributeError, StandardAttributes


logger = logging.getLogger(__name__)


class Auth_LDAP(Auth_UsernamePasswordBase):
    def check_user_pass(self, username, password):
        l = ldap.initialize(self.config['server_url'])
        l.simple_bind_s(self.config['bind_dn'] % {'username': username}, password)
        scope = ldap.SCOPE_BASE
        if self.config['search_depth'] == 1:
            scope = ldap.SCOPE_ONELEVEL
        elif self.config['search_depth'] == -1:
            scope = ldap.SCOPE_SUBSTREE
        result = l.search_s(self.config['search_root'],
                            scope,
                            self.config['search_filter'] % {'username': username})
        groups = l.search_s(self.config['group_search_root'],
                            ldap.SCOPE_SUBTREE,
                            self.config['group_search_filter'] % {'username': username})
        if result is None or result == []:
            raise Exception('User object could not be found!')
        elif len(result) > 1:
            raise Exception('No unique user object could be found!')
        else:
            result = result[0][1]
            result['groups'] = [group[1]['cn'][0] for group in groups]
            for to_ignore in self.config['to_ignore']:
                result[to_ignore] = None
            return result

    def get_username(self):
        if not self.logged_in():
            raise UnauthorizedError
        return self._user[self.config['username_attribute']][0]

    def get_attribute(self, attribute):
        if not self.logged_in():
            raise UnauthorizedError
        attribute = attribute.__str__()
        if attribute in self.config['attribute_mapping'].keys():
            if self.config['attribute_mapping'][attribute] in self._user:
                value = self._user[self.config['attribute_mapping'][attribute]]
                if isinstance(value, list):
                    if len(value) > 0:
                        return value[0]
                else:
                    return value
        raise UnknownAttributeError

    def get_groups(self):
        return self._user['groups']

    def get_clas(self):
        return []

    def used_multi_factor(self):
        return False

    def used_multi_factor_physical(self):
        return False

    def used_phishing_resistant(self):
        return False
