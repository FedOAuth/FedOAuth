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
from fedoauth.auth.base import Auth_UsernamePasswordBase, UnauthorizedError, \
    UnknownAttributeError

import logging
logger = logging.getLogger(__name__)


class Auth_Dummy(Auth_UsernamePasswordBase):
    def check_user_pass(self, username, password):
        # Yes, this is vulnerable to a timing attack and more
        # but this is a dummy module meant as example
        if username == self.config['username'] and \
                password == self.config['password']:
            return username
        else:
            return False

    def get_username(self):
        return self.config['username']

    def get_attribute(self, attribute):
        if not self.logged_in():
            raise UnauthorizedError
        attribute = attribute.__str__()
        if attribute == 'password':
            attribute = None
        if attribute in self.config:
            return self.config[attribute]
        raise UnknownAttributeError

    def get_groups(self, **filterargs):
        return []

    def get_clas(self):
        return []

    def used_multi_factor(self):
        return False

    def used_multi_factor_physical(self):
        return False

    def used_phishing_resistant(self):
        return False
