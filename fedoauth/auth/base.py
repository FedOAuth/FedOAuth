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
class Auth_Base:
    def __init__(self, config):
        pass

    def start_authentication(self):
        raise NotImplementedError()

    def api_authenticate(self, post_data):
        raise NotImplementedError()

    def get_persona_auth_base(self):
        raise NotImplementedError()

    def logged_in(self):
        raise NotImplementedError()

    def get_username(self):
        raise NotImplementedError()

    def get_sreg(self):
        raise NotImplementedError()

    def get_groups(self):
        raise NotImplementedError()

    def used_multi_factor(self):
        raise NotImplementedError()

    def used_multi_factor_physical(self):
        raise NotImplementedError()

    def used_phishing_resistant(self):
        raise NotImplementedError()
