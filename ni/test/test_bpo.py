from http import client
import unittest
from unittest import mock

from . import util
from .. import abc
from .. import bpo


class OfflineTests(util.TestCase):

    def test_failure(self):
        host = bpo.Host(util.FakeServerHost())
        failed_response = util.FakeResponse(status=404)
        fake_session = util.FakeSession(response=failed_response)
        with mock.patch('ni.abc.session', fake_session):
            with self.assertRaises(client.HTTPException):
                self.run_awaitable(host.check(['brettcannon']))


class NetworkTests(util.TestCase):

    signed_cla = 'brettcannon'
    not_signed_cla = 'the-knights-who-say-ni'

    def setUp(self):
        self.bpo = bpo.Host(util.FakeServerHost())

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
