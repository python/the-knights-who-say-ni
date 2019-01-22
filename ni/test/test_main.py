import http
import unittest.mock as mock
from typing import FrozenSet

from .. import __main__
from .. import abc as ni_abc
from .. import github
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

    async def process(self, server, request, session):
        """Process a request into a contribution."""
        if self._raise is not None:
            raise self._raise
        return self

    async def usernames(self):
        """Return an iterable of all the contributors' usernames."""
        return frozenset(self._usernames)

    async def update(self, status):
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
        self.assertEqual(cla.usernames, frozenset(usernames))
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

    def test_contrib_secret_given(self):
        status = ni_abc.Status.signed
        server = util.FakeServerHost()
        server.secret = "secret"
        cla = FakeCLAHost(status)
        contrib = github.Host
        request = util.FakeRequest()
        with mock.patch('ni.__main__.ContribHost', contrib):
            responder = __main__.handler(util.FakeSession, server, cla)
            response = self.run_awaitable(responder(request))
        # Fails due to secret being provided but response not signed.
        self.assertEqual(response.status, 500)

    def test_contrib_secret_missing(self):
        status = ni_abc.Status.signed
        server = util.FakeServerHost()
        cla = FakeCLAHost(status)
        contrib = github.Host
        request = util.FakeRequest()
        request.headers["x-hub-signature"] = "sha1=signed"
        with mock.patch('ni.__main__.ContribHost', contrib):
            responder = __main__.handler(util.FakeSession, server, cla)
            response = self.run_awaitable(responder(request))
        # Fails due to secret being provided but response not signed.
        self.assertEqual(response.status, 500)

    def test_no_trusted_users(self):
        usernames = ['miss-islington', 'bedevere-bot']
        status = ni_abc.Status.signed
        server = util.FakeServerHost()
        server.trusted_usernames = ''
        cla = FakeCLAHost(status)
        contrib = FakeContribHost(usernames)
        request = util.FakeRequest()
        with mock.patch('ni.__main__.ContribHost', contrib):
            responder = __main__.handler(util.FakeSession, server, cla)
            response = self.run_awaitable(responder(request))
        self.assertEqual(response.status, 200)
        self.assertEqual(cla.usernames, frozenset(usernames))
        self.assertEqual(contrib.status, status)

    def test_not_comma_separated_trusted_users(self):
        usernames = ['miss-islington', 'bedevere-bot']
        status = ni_abc.Status.signed
        server = util.FakeServerHost()
        server.trusted_usernames = 'bedevere-bot'
        cla = FakeCLAHost(status)
        contrib = FakeContribHost(usernames)
        request = util.FakeRequest()
        with mock.patch('ni.__main__.ContribHost', contrib):
            responder = __main__.handler(util.FakeSession, server, cla)
            response = self.run_awaitable(responder(request))
        self.assertEqual(response.status, 200)
        self.assertEqual(cla.usernames, frozenset(['miss-islington']))

    def test_comma_separated_trusted_users(self):
        usernames = ['brettcannon', 'miss-islington', 'bedevere-bot']
        status = ni_abc.Status.signed
        server = util.FakeServerHost()
        server.trusted_usernames = 'bedevere-bot,miss-islington'
        cla = FakeCLAHost(status)
        contrib = FakeContribHost(usernames)
        request = util.FakeRequest()
        with mock.patch('ni.__main__.ContribHost', contrib):
            responder = __main__.handler(util.FakeSession, server, cla)
            response = self.run_awaitable(responder(request))
        self.assertEqual(response.status, 200)
        self.assertEqual(cla.usernames, frozenset(['brettcannon']))

    def test_comma_separated_trusted_users_with_spaces(self):
        usernames = ['brettcannon', 'miss-islington', 'bedevere-bot']

        status = ni_abc.Status.signed
        server = util.FakeServerHost()
        server.trusted_usernames = 'bedevere-bot, miss-islington'
        cla = FakeCLAHost(status)
        contrib = FakeContribHost(usernames)
        request = util.FakeRequest()
        with mock.patch('ni.__main__.ContribHost', contrib):
            responder = __main__.handler(util.FakeSession, server, cla)
            response = self.run_awaitable(responder(request))
        self.assertEqual(response.status, 200)
        self.assertEqual(cla.usernames, frozenset(['brettcannon']))

    def test_trusted_users_ignored_case(self):
        usernames = ['brettcannon', 'miss-islington', 'bedevere-bot']

        status = ni_abc.Status.signed
        server = util.FakeServerHost()
        server.trusted_usernames = 'bedevere-bot, Miss-Islington'
        cla = FakeCLAHost(status)
        contrib = FakeContribHost(usernames)
        request = util.FakeRequest()
        with mock.patch('ni.__main__.ContribHost', contrib):
            responder = __main__.handler(util.FakeSession, server, cla)
            response = self.run_awaitable(responder(request))
        self.assertEqual(response.status, 200)
        self.assertEqual(cla.usernames, frozenset(['brettcannon']))

    def test_no_usernames(self):
        usernames: FrozenSet[str] = frozenset()
        status = ni_abc.Status.not_signed
        server = util.FakeServerHost()
        server.trusted_usernames = 'bedevere-bot, miss-islington'
        cla = FakeCLAHost(status)
        contrib = FakeContribHost(usernames)
        request = util.FakeRequest()
        with mock.patch('ni.__main__.ContribHost', contrib):
            responder = __main__.handler(util.FakeSession, server, cla)
            response = self.run_awaitable(responder(request))
        self.assertEqual(response.status, 200)
        self.assertEqual(cla.usernames, frozenset())
        self.assertEqual(contrib.status, status)

    def test_all_trusted_users(self):
        usernames = ['bedevere-bot', 'miss-islington']
        status = ni_abc.Status.signed
        server = util.FakeServerHost()
        server.trusted_usernames = 'bedevere-bot, miss-islington'
        cla = FakeCLAHost(status)
        contrib = FakeContribHost(usernames)
        request = util.FakeRequest()
        with mock.patch('ni.__main__.ContribHost', contrib):
            responder = __main__.handler(util.FakeSession, server, cla)
            response = self.run_awaitable(responder(request))
        self.assertEqual(response.status, 200)
        self.assertEqual(cla.usernames, frozenset([]))
        self.assertEqual(contrib.status, status)
