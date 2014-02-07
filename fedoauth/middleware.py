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
from flask.sessions import SessionInterface

from fedoauth.model import DBSession


class DBSessionMiddleware(SessionInterface):
    pickle_based = True

    def open_session(self, app, request):
        return DBSession.open_session(app, request)

    def save_session(self, app, session, response):
        if session:
            session.save_session(app, response)
        else:
            session.delete_session(app, response)
