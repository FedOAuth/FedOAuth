import os
import tempfile
import unittest
import fas_openid
from openid.association import Association
from fas_openid import APP as app
from fas_openid import model
from fas_openid.model import FASOpenIDStore
from time import time


class FasOpenIDStoreTest(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.filename = tempfile.mkstemp()
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///%s' % self.filename
        app.config['TESTING'] = True
        model.create_tables(app.config['SQLALCHEMY_DATABASE_URI'], True)
        self.store = FASOpenIDStore()

#    def tearDown(self):
#        os.close(self.db_fd)
#        os.unlink(self.filename)

    def test_assocications(self):
        self.store.storeAssociation("me-local",
                                    Association("handle1", "oursecret",
                                                time(), 50, "HMAC-SHA1"))
        assert self.store.getAssociation("me-local", "handle1")
        assert self.store.getAssociation("me-local", "handle2") is None
        assert self.store.removeAssociation("me-local", "handle1")
        assert not self.store.removeAssociation("me-local", "handle2")
        assert self.store.getAssociation("me-local", "handle1") is None

    def test_nonce(self):
        tm = time()
        assert self.store.useNonce("me-local", tm, "salt1")
        assert self.store.useNonce("me-local", tm, "salt2")
        assert not self.store.useNonce("me-local", tm, "salt1")
        assert not self.store.useNonce("me-local", 0, "salt3")

if __name__ == '__main__':
    unittest.main()
