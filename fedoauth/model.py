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
from fedoauth import db
from sqlalchemy.types import PickleType
try:
    from sqlalchemy.ext.mutable import MutableDict
except:
    from fedoauth.utils import BackportedMutableDict as MutableDict
from openid.association import Association as openid_assoc
from openid.store.nonce import SKEW as NonceSKEW
from openid.store.interface import OpenIDStore
from uuid import uuid4
from datetime import timedelta, datetime
import time
import logging


logger = logging.getLogger(__name__)


class Transaction(db.Model):
    key = db.Column(db.String(32), nullable=False, primary_key=True)
    startmoment = db.Column(db.DateTime(timezone=False), nullable=False)
    values = db.Column(MutableDict.as_mutable(PickleType), nullable=False)

    def __init__(self):
        self.key = uuid4().hex
        self.startmoment = datetime.now()
        self.values = MutableDict()
        self.values['check'] = uuid4().hex

    def __str__(self):
        return 'Transaction %s' % self.key


class Remembered(db.Model):
    # The primary key will differ per type of remembered data
    type = db.Column(db.String(32), nullable=False, primary_key=True)
    key = db.Column(db.String(512), nullable=False, primary_key=True)
    expiry = db.Column(db.DateTime, nullable=True)
    data = db.Column(db.Text, nullable=True)

    def __init__(self, type, key, expiry, data):
        self.type = type
        self.key = key
        self.data = data
        self.expiry = expiry
        logger.debug('Remembering type %s with key %s until %s',
                     type,
                     key,
                     expiry)

    def save(self):
        db.session.add(self)
        db.session.commit()

    @staticmethod
    def getremembered(type, *key):
        key = '-'.join(key)

        logger.debug('Key: %s' % key)

        remembered = Remembered.query.filter_by(
            type=type,
            key=key).first()
        if remembered:
            logger.debug('Remembered found')
            if remembered.expiry is None:
                logger.debug('Always valid')
                return remembered
            else:
                delta = remembered.expiry - datetime.now()
                logger.debug('Delta: %s', delta)
                if delta > timedelta():
                    return remembered
                else:
                    Remembered.query.filter_by(
                        type=type,
                        key=key).delete()
        return None

    @staticmethod
    def remember(type, timedelta, data, *key):
        key = '-'.join(key)

        return Remembered(type, key, datetime.now() + timedelta, data).save()

    @staticmethod
    def rememberForDays(type, rememberForDays, data, *key):
        return Remembered.remember(type,
                                   timedelta(rememberForDays),
                                   data,
                                   *key)

    @staticmethod
    def cleanup():
        return Remembered.query.filter(Remembered.expiry < datetime.now()).delete()


class OpenIDAssociation(db.Model):
    server_url = db.Column(db.String(512), nullable=False, primary_key=True)
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


class OpenIDNonce(db.Model):
    server_url = db.Column(db.String(512), nullable=False, primary_key=True)
    salt = db.Column(db.String(40), nullable=False, primary_key=True)
    timestamp = db.Column(db.Integer, nullable=False, primary_key=True)

    def __init__(self, server_url, salt, timestamp):
        self.server_url = server_url
        self.salt = salt
        self.timestamp = timestamp


class OpenIDStore(OpenIDStore):
    def storeAssociation(self, server_url, association):
        assoc = OpenIDAssociation(server_url, association)
        db.session.add(assoc)
        db.session.commit()

    def getAssociation(self, lookup_server_url, lookup_handle=None):
        if lookup_handle is None:
            # Get assoc only by server_url, we need some filtering on this one
            assoc = OpenIDAssociation.query.filter_by(
                server_url=lookup_server_url).order_by(
                OpenIDAssociation.issued.desc()).first()
        else:
            assoc = OpenIDAssociation.query.filter_by(
                server_url=lookup_server_url,
                handle=lookup_handle).order_by(
                OpenIDAssociation.issued.desc()).first()
        if not assoc:
            return None
        if (assoc.issued + assoc.lifetime) < time.time():
            db.session.delete(assoc)
            db.session.commit()
            return None
        return openid_assoc(assoc.handle, assoc.secret, assoc.issued,
                            assoc.lifetime, assoc.assoc_type)

    def removeAssociation(self, lookup_server_url, lookup_handle):
        return OpenIDAssociation.query.filter_by(
            server_url=lookup_server_url,
            handle=lookup_handle).delete() > 0

    def useNonce(self, lookup_server_url, lookup_timestamp, lookup_salt):
        if abs(lookup_timestamp - time.time()) > NonceSKEW:
            return False
        results = OpenIDNonce.query.filter_by(
            server_url=lookup_server_url,
            timestamp=lookup_timestamp,
            salt=lookup_salt).all()
        if results:
            return False
        else:
            nonce = OpenIDNonce(lookup_server_url,
                                lookup_salt,
                                lookup_timestamp)
            db.session.add(nonce)
            db.session.commit()
            return True

    def cleanupNonces(self):
        return OpenIDNonce.query.filter(
            OpenIDNonce.timestamp < (time.time() - NonceSKEW)).delete()

    def cleanupAssociations(self):
        return OpenIDAssociation.query.filter(
            (OpenIDAssociation.issued + OpenIDAssociation.lifetime) <
            time.time()).delete()
