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
