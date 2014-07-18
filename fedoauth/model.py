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
from fedoauth import dbengine, dbsession
from sqlalchemy.ext.declarative import declarative_base
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

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Text,
    LargeBinary,
    Integer,
)

from fedoauth.utils import _QueryProperty


logger = logging.getLogger(__name__)
BASE = declarative_base(bind=dbengine)
BASE.query = _QueryProperty(dbsession)


class Transaction(BASE):
    __tablename__ = 'transaction'
    key = Column(String(32), nullable=False, primary_key=True)
    startmoment = Column(DateTime(timezone=False), nullable=False)
    values = Column(MutableDict.as_mutable(PickleType), nullable=False)

    def __init__(self):
        self.key = uuid4().hex
        self.startmoment = datetime.now()
        self.values = MutableDict()
        self.values['check'] = uuid4().hex

    def __str__(self):
        return 'Transaction %s' % self.key


class Remembered(BASE):
    __tablename__ = 'remembered'
    # The primary key will differ per type of remembered data
    type = Column(String(32), nullable=False, primary_key=True)
    key = Column(String(512), nullable=False, primary_key=True)
    expiry = Column(DateTime, nullable=True)
    data = Column(Text, nullable=True)

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
        dbsession.add(self)
        dbsession.commit()

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


class OpenIDAssociation(BASE):
    __tablename__ = 'openid_association'
    server_url = Column(String(512), nullable=False, primary_key=True)
    handle = Column(String(128), nullable=False, primary_key=True)
    secret = Column(LargeBinary(128), nullable=False)
    issued = Column(Integer, nullable=False)
    lifetime = Column(Integer, nullable=False)
    assoc_type = Column(String(64), nullable=False)

    def __init__(self, server_url, association):
        self.server_url = server_url
        self.handle = association.handle
        self.secret = association.secret
        self.issued = association.issued
        self.lifetime = association.lifetime
        self.assoc_type = association.assoc_type


class OpenIDNonce(BASE):
    __tablename__ = 'openid_nonce'
    server_url = Column(String(512), nullable=False, primary_key=True)
    salt = Column(String(40), nullable=False, primary_key=True)
    timestamp = Column(Integer, nullable=False, primary_key=True)

    def __init__(self, server_url, salt, timestamp):
        self.server_url = server_url
        self.salt = salt
        self.timestamp = timestamp


class OpenIDStore(OpenIDStore):
    def storeAssociation(self, server_url, association):
        assoc = OpenIDAssociation(server_url, association)
        dbsession.add(assoc)
        dbsession.commit()

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
            dbsession.delete(assoc)
            dbsession.commit()
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
            dbsession.add(nonce)
            dbsession.commit()
            return True

    def cleanupNonces(self):
        return OpenIDNonce.query.filter(
            OpenIDNonce.timestamp < (time.time() - NonceSKEW)).delete()

    def cleanupAssociations(self):
        return OpenIDAssociation.query.filter(
            (OpenIDAssociation.issued + OpenIDAssociation.lifetime) <
            time.time()).delete()
