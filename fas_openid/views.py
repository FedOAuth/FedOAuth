from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash

from fas_openid import app


@app.route('/')
def view_main():
    return render_template('index.html')
