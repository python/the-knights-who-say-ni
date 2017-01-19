from http import client
import json
import unittest
from unittest import mock

from . import util
from .. import abc as ni_abc
from .. import bpo


class OfflineTests(util.TestCase):

    def test_failure(self):
        host = bpo.Host(util.FakeServerHost())
        failed_response = util.FakeResponse(status=404)
        fake_session = util.FakeSession(response=failed_response)
        with mock.patch('ni.abc.session', fake_session):
            with self.assertRaises(client.HTTPException):
                self.run_awaitable(host.check(['brettcannon']))

    def test_filter_extraneous_data(self):
        host = bpo.Host(util.FakeServerHost())
        response_data = {'web-flow': None, 'brettcannon': True}
        fake_response = util.FakeResponse(data=json.dumps(response_data))
        fake_session = util.FakeSession(response=fake_response)
        with mock.patch('ni.abc.session', fake_session):
            result = self.run_awaitable(host.check(['brettcannon']))
        self.assertEqual(result, ni_abc.Status.signed)

    def test_missing_data(self):
        host = bpo.Host(util.FakeServerHost())
        response_data = {'web-flow': None}
        fake_response = util.FakeResponse(data=json.dumps(response_data))
        fake_session = util.FakeSession(response=fake_response)
        with mock.patch('ni.abc.session', fake_session):
            with self.assertRaises(ValueError):
                self.run_awaitable(host.check(['brettcannon']))

    def test_bad_data(self):
        host = bpo.Host(util.FakeServerHost())
        response_data = {'brettcannon': 42}
        fake_response = util.FakeResponse(data=json.dumps(response_data))
        fake_session = util.FakeSession(response=fake_response)
        with mock.patch('ni.abc.session', fake_session):
            with self.assertRaises(TypeError):
                self.run_awaitable(host.check(['brettcannon']))


class NetworkTests(util.TestCase):

    signed_cla = 'brettcannon'
    not_signed_cla = 'the-knights-who-say-ni'

    def setUp(self):
        self.bpo = bpo.Host(util.FakeServerHost())

    def test_signed(self):
        result = self.run_awaitable(self.bpo.check([self.signed_cla]),
                                    loop=ni_abc.loop())
        self.assertEqual(result, ni_abc.Status.signed)

    def test_not_signed(self):
        usernames = [self.signed_cla, self.not_signed_cla]
        result = self.run_awaitable(self.bpo.check(usernames),
                                    loop=ni_abc.loop())
        self.assertEqual(result, ni_abc.Status.not_signed)

    def test_missing_username(self):
        usernames = [self.signed_cla, 'fdsfdsdooisadfsadnfasdfdsf']
        result = self.run_awaitable(self.bpo.check(usernames),
                                    loop=ni_abc.loop())
        self.assertEqual(result, ni_abc.Status.username_not_found)


if __name__ == '__main__':
    unittest.main()
