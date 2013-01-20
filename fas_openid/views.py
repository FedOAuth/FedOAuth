from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash

from model import FASOpenIDStore

from fas_openid import APP as app, FAS

from flask_fas import fas_login_required

@app.route('/')
def view_main():
    return render_template('index.html', text='main')

@app.route('/logout/')
def auth_logout():
    if not g.fas_user:
        return redirect(url_for('view_main'))
    FAS.logout()
    flash('You have been logged out')
    return redirect(url_for('view_main'))

@app.route('/login/', methods=['GET','POST'])
def auth_login():
    if not 'next' in request.values:
        return redirect(url_for('view_main'))
    nextpage = request.values['next']
    if g.fas_user:
        return redirect(nextpage)
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        result = FAS.login(username, password)
        if result:
            return redirect(nextpage)
        else:
            flash('Incorrect username or password')
    return render_template('login.html', nextpage=nextpage)

@app.route('/test/')
@fas_login_required
def view_test():
    return render_template('index.html', text='TESTJE. User: %s' % g.fas_user)
