from flask.sessions import SessionInterface

from fas_openid.model import DBSession

from fas_openid import db


class DBSessionMiddleware(SessionInterface):
    def open_session(self, app, request):
        return DBSession.open_session(app, request)

    def save_session(self, app, session, response):
        session.save_session(app, response)
