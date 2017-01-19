import http
import unittest
from unittest import mock

from .. import __main__
from .. import abc as ni_abc
from . import util


class FakeCLAHost(ni_abc.CLAHost):

    """Abstract base class for the CLA records platform."""

    def __init__(self, status=None):
        self._status = status

    async def check(self, client, usernames):
        """Check if all of the specified usernames have signed the CLA."""
        self.usernames = usernames
        return self._status


class FakeContribHost(ni_abc.ContribHost):

    """Abstract base class for the contribution/pull request platform."""

    def __init__(self, usernames=[], raise_=None):
        self._usernames = usernames
        self._raise = raise_

    @property
    def route(self):
        return '*', '/'  # pragma: no cover

    async def process(self, server, request):
        """Process a request into a contribution."""
        if self._raise is not None:
            raise self._raise
        return self

    async def usernames(self, client):
        """Return an iterable of all the contributors' usernames."""
        return self._usernames

    async def update(self, client, status):
        """Update the contribution with the status of CLA coverage."""
        self.status = status


class HandlerTest(util.TestCase):

    def test_response(self):
        # Success case.
        usernames = ['brettcannon']
        status = ni_abc.Status.signed
        server = util.FakeServerHost()
        cla = FakeCLAHost(status)
        contrib = FakeContribHost(usernames)
        request = util.FakeRequest()
        with mock.patch('ni.__main__.ContribHost', contrib):
            responder = __main__.handler(util.FakeSession, server, cla)
            response = self.run_awaitable(responder(request))
        self.assertEqual(response.status, 200)
        self.assertEqual(cla.usernames, usernames)
        self.assertEqual(contrib.status, status)

    def test_ResponseExit(self):
        # Test when ResponseExit is raised.
        server = util.FakeServerHost()
        cla = FakeCLAHost()
        text = 'test'
        response_exit = ni_abc.ResponseExit(status=http.HTTPStatus.FOUND,
                                         text=text)
        contrib = FakeContribHost(raise_=response_exit)
        with mock.patch('ni.__main__.ContribHost', contrib):
            responder = __main__.handler(util.FakeSession, server, cla)
            response = self.run_awaitable(responder(util.FakeRequest()))
        self.assertEqual(response.status, http.HTTPStatus.FOUND)
        self.assertEqual(response.text, text)

    def test_unexpected_exception(self):
        # Test when a non-ResponseExit exception is raised.
        server = util.FakeServerHost()
        cla = FakeCLAHost()
        exc = Exception('test')
        contrib = FakeContribHost(raise_=exc)
        with mock.patch('ni.__main__.ContribHost', contrib):
            responder = __main__.handler(util.FakeSession, server, cla)
            response = self.run_awaitable(responder(util.FakeRequest()))
        self.assertEqual(response.status, http.HTTPStatus.INTERNAL_SERVER_ERROR)
        self.assertEqual(server.logged_exc, exc)
