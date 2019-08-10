import asyncio
from http import client
import json
import unittest

import aiohttp

from . import util
from .. import abc as ni_abc
from .. import bpo


class OfflineTests(util.TestCase):

    def test_failure(self):
        host = bpo.Host(util.FakeServerHost())
        failed_response = util.FakeResponse(status=404)
        fake_session = util.FakeSession(response=failed_response)
        with self.assertRaises(client.HTTPException):
            self.run_awaitable(host.problems(fake_session, {'brettcannon'}))

    def test_filter_extraneous_data(self):
        host = bpo.Host(util.FakeServerHost())
        response_data = {'web-flow': None, 'brettcannon': True}
        fake_response = util.FakeResponse(data=json.dumps(response_data))
        fake_session = util.FakeSession(response=fake_response)
        result = self.run_awaitable(host.problems(fake_session, {'brettcannon'}))
        self.assertEqual(result, {ni_abc.Status.username_not_found: {'web-flow'}})

    def test_missing_data(self):
        host = bpo.Host(util.FakeServerHost())
        response_data = {'web-flow': None}
        fake_response = util.FakeResponse(data=json.dumps(response_data))
        fake_session = util.FakeSession(response=fake_response)
        with self.assertRaises(ValueError):
            self.run_awaitable(host.problems(fake_session, {'brettcannon'}))

    def test_bad_data(self):
        host = bpo.Host(util.FakeServerHost())
        response_data = {'brettcannon': 42}
        fake_response = util.FakeResponse(data=json.dumps(response_data))
        fake_session = util.FakeSession(response=fake_response)
        with self.assertRaises(TypeError):
            self.run_awaitable(host.problems(fake_session, {'brettcannon'}))


class SessionOnDemand:

    """Role session creation and HTTP requesting in a single object.

    aiohttp raises a warning if a ClientSession is created outside of a
    coroutine. To avoid this issue, this class acts as an async context
    manager which both creates a session and makes a GET request.
    """

    def __init__(self, loop):
        self.loop = loop

    def get(self, url):
        self.url = url
        return self

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.session_ctx = await self.session.__aenter__()
        self.getter_ctx = self.session_ctx.get(self.url)
        return await self.getter_ctx.__aenter__()

    async def __aexit__(self, *args):
        await self.getter_ctx.__aexit__(*args)
        await self.session_ctx.__aexit__(*args)


class NetworkTests(util.TestCase):

    signed_cla = 'brettcannon'
    not_signed_cla = 'the-knights-who-say-ni'

    def setUp(self):
        self.bpo = bpo.Host(util.FakeServerHost())
        self.loop = asyncio.get_event_loop()
        self.session = SessionOnDemand(self.loop)

    def test_signed(self):
        result = self.run_awaitable(
                self.bpo.problems(self.session, [self.signed_cla]),
                loop=self.loop)
        self.assertEqual(result, {})

    def test_not_signed(self):
        usernames = [self.signed_cla, self.not_signed_cla]
        result = self.run_awaitable(self.bpo.problems(self.session, usernames),
                                    loop=self.loop)
        self.assertEqual(result, {ni_abc.Status.not_signed: {self.not_signed_cla}})

    def test_missing_username(self):
        username_not_found = 'fdsfdsdooisadfsadnfasdfdsf'
        usernames = [self.signed_cla, username_not_found]
        result = self.run_awaitable(self.bpo.problems(self.session, usernames),
                                    loop=self.loop)
        self.assertEqual(result, {ni_abc.Status.username_not_found: {username_not_found}})


if __name__ == '__main__':
    unittest.main()
