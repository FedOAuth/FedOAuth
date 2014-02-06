from fedoauth import db, get_auth_module
from datetime import datetime
from flask.sessions import SessionMixin
from openid.association import Association as openid_assoc
from openid.store.nonce import SKEW as NonceSKEW
from openid.store.interface import OpenIDStore
import time
import cPickle as serializer
import uuid
from UserDict import DictMixin


class DBSession(db.Model, SessionMixin, DictMixin):
    sessionid = db.Column(db.String(32), primary_key=True)
    remote_addr = db.Column(db.String(50), nullable=False)
    created = db.Column(db.DateTime, nullable=False)
    saved = db.Column(db.DateTime, nullable=False)
    rawdata = db.Column(db.LargeBinary, nullable=False)
    data_cache = None

    @property
    def data(self):
        if self.data_cache is None:
            self.data_cache = serializer.loads(self.rawdata)
        return self.data_cache

    new = False
    modified = False

    def __repr__(self):
        return 'DBSession(%s, %s, %s, %s, %s)' % (self.sessionid,
                                                  self.remote_addr,
                                                  self.created,
                                                  self.saved,
                                                  self.data)

    def __init__(self):
        self.sessionid = uuid.uuid1().hex
        self.created = datetime.now()
        self.saved = datetime.now()
        self.rawdata = serializer.dumps({})
        self.save()

    def save(self):
        self.modified = True

    def __delitem__(self, key):
        return self.data.__delitem__(key)

    def __getitem__(self, key):
        return self.data.__getitem__(key)

    def __setitem__(self, key, value):
        return self.data.__setitem__(key, value)

    def keys(self):
        return self.data.keys()

    @classmethod
    def open_session(cls, app, request):
        if not request.path == '/' and not request.path == '/logout/' \
                and not get_auth_module().is_dynamic_content(request.path):
            return None
        request.path
        sessionid = request.cookies.get('sessionid')

        if sessionid:
            retrieved = DBSession.query.filter_by(sessionid=sessionid,
                                                  remote_addr=request.remote_addr).first()
            if not retrieved is None:
                return retrieved

        new = DBSession()
        new.remote_addr = request.remote_addr
        new.new = True
        new.modified = True
        db.session.add(new)
        db.session.commit()
        return new

    def save_session(self, app, response):
        if self.modified:
            self.saved = datetime.now()
            self.rawdata = serializer.dumps(self.data)
            db.session.add(self)
            db.session.commit()
            response.set_cookie('sessionid', self.sessionid)

    def delete(self):
        self.data = {}
        self.save()
        DBSession.query.filter_by(sessionid=self.sessionid,
                                  remote_addr=self.remote_addr).delete()

    def delete_session(self, app, response):
        DBSession.query.filter_by(sessionid=self.sessionid,
                                  remote_addr=self.remote_addr).delete()
        response.delete_cookie('sessionid')


class Association(db.Model):
    server_url = db.Column(db.String(2048), nullable=False, primary_key=True)
    handle = db.Column(db.String(128), nullable=False, primary_key=True)
    secret = db.Column(db.LargeBinary(128), nullable=False)
    issued = db.Column(db.Integer, nullable=False)
    lifetime = db.Column(db.Integer, nullable=False)
    assoc_type = db.Column(db.String(64), nullable=False)

    def __init__(self, server_url, association):
        self.server_url = server_url
        self.handle = association.handle
        self.secret = association.secret
        self.issued = association.issued
        self.lifetime = association.lifetime
        self.assoc_type = association.assoc_type


class Nonce(db.Model):
    server_url = db.Column(db.String(2048), nullable=False, primary_key=True)
    salt = db.Column(db.String(40), nullable=False, primary_key=True)
    timestamp = db.Column(db.Integer, nullable=False, primary_key=True)

    def __init__(self, server_url, salt, timestamp):
        self.server_url = server_url
        self.salt = salt
        self.timestamp = timestamp


class FedOAuthOpenIDStore(OpenIDStore):
    def storeAssociation(self, server_url, association):
        assoc = Association(server_url, association)
        db.session.add(assoc)
        db.session.commit()

    def getAssociation(self, lookup_server_url, lookup_handle=None):
        if lookup_handle is None:
            # Get assoc only by server_url, we need some filtering on this one
            assoc = Association.query.filter_by(
                server_url=lookup_server_url).order_by(
                    Association.issued.desc()).first()
        else:
            assoc = Association.query.filter_by(
                server_url=lookup_server_url,
                handle=lookup_handle).order_by(
                    Association.issued.desc()).first()
        if not assoc:
            return None
        if (assoc.issued + assoc.lifetime) < time.time():
            db.session.delete(assoc)
            db.session.commit()
            return None
        return openid_assoc(assoc.handle, assoc.secret, assoc.issued,
                            assoc.lifetime, assoc.assoc_type)

    def removeAssociation(self, lookup_server_url, lookup_handle):
        return Association.query.filter_by(
            server_url=lookup_server_url,
            handle=lookup_handle).delete() > 0

    def useNonce(self, lookup_server_url, lookup_timestamp, lookup_salt):
        if abs(lookup_timestamp - time.time()) > NonceSKEW:
            return False
        results = Nonce.query.filter_by(
            server_url=lookup_server_url,
            timestamp=lookup_timestamp,
            salt=lookup_salt).all()
        if results:
            return False
        else:
            nonce = Nonce(lookup_server_url, lookup_salt, lookup_timestamp)
            db.session.add(nonce)
            db.session.commit()
            return True

    def cleanupNonces(self):
        return Nonce.query.filter(
            Nonce.timestamp < (time.time() - NonceSKEW)).delete()

    def cleanupAssociations(self):
        return Association.query.filter(
            (Association.issued + Association.lifetime) < time.time()).delete()


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def create_tables(db_url, debug=False):
    """ Create the tables in the database using the information from the
    url obtained.

    :arg db_url, URL used to connect to the database. The URL contains
    information with regards to the database engine, the host to connect
    to, the user and password and the database name.
      ie: <engine>://<user>:<password>@<host>/<dbname>
    :kwarg debug, a boolean specifying wether we should have the verbose
    output of sqlalchemy or not.
    :return a session that can be used to query the database.
    """
    engine = create_engine(db_url, echo=debug)
    db.Model.metadata.create_all(engine)

    sessionmak = sessionmaker(bind=engine)
    return sessionmak()
