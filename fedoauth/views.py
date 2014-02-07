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
from flask import redirect, url_for, render_template, flash
from flaskext.babel import gettext as _

from fedoauth import APP as app, get_session
from views_openid import view_openid_main


@app.route('/robots.txt')
def view_robots():
    return 'User-Agent: *\nDisallow: /'


@app.route('/', methods=['GET', 'POST'])
def view_main():
    # We are using view_openid_main because this makes sure that the
    #  website root is also a valid OpenID endpoint URL
    return view_openid_main()


@app.route('/logout/')
def auth_logout():
    # No check if we are logged in, as we can always delete the session
    get_session().delete()
    flash(_('You have been logged out'))
    return redirect(url_for('view_main'))
