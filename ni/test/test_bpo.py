import unittest

from . import util
from .. import abc
from .. import bpo


class BPOTests(util.TestCase):

    signed_cla = 'brettcannon'
    not_signed_cla = 'the-knights-who-say-ni'

    @classmethod
    def tearDownClass(cls):
        session = abc.session()
        session.close()
        abc.session = abc._session_factory()
        super().tearDownClass()

    def setUp(self):
        self.bpo = bpo.Host()

    def test_signed(self):
        result = self.run_awaitable(self.bpo.check([self.signed_cla]),
                                    loop=abc.loop())
        self.assertEqual(result, abc.Status.signed)

    def test_not_signed(self):
        usernames = [self.signed_cla, self.not_signed_cla]
        result = self.run_awaitable(self.bpo.check(usernames),
                                    loop=abc.loop())
        self.assertEqual(result, abc.Status.not_signed)

    def test_missing_username(self):
        usernames = [self.signed_cla, 'fdsfdsdooisadfsadnfasdfdsf']
        result = self.run_awaitable(self.bpo.check(usernames),
                                    loop=abc.loop())
        self.assertEqual(result, abc.Status.username_not_found)


if __name__ == '__main__':
    unittest.main()
