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
