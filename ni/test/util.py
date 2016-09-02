import asyncio
import unittest

from aiohttp import web

from .. import abc


class FakeRequest:

    """Provide a base class for faking requests.

    Inheriting from web.Request is bad as the docs explicitly say not to create
    instances manually. To work around that this faked request is provided.
    http://aiohttp.readthedocs.org/en/stable/web_reference.html#aiohttp.web.Request
    """

    def __init__(self, payload={}, content_type='application/json'):
        self.content_type = content_type
        self._payload = payload

    async def json(self):
        return self._payload


class FakeResponse(web.Response):

    def __init__(self, *args, data=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._data = data

    async def json(self):
        return self._data

    async def text(self):
        return self._data


class FakeSession:

    def __init__(self, *, data=None, response=None):
        if response is None:
            response = FakeResponse(status=200, data=data)
        self._response = response

    def __call__(self):
        return self

    async def __aenter__(self):
        return self._response

    async def __aexit__(self, exc_type, exc, tb):
        pass

    def get(self, url, headers=None):
        self.method = 'GET'
        self.url = url
        self._response.url = url
        self.headers = headers
        return self

    def post(self, url, data, headers):
        self.method = 'POST'
        self.url = url
        self._response.url = url
        self.data = data
        self.headers = headers
        return self

    def delete(self, url, headers=None):
        self.method = 'DELETE'
        self.url = url
        self._response.url = url
        self.headers = headers
        return self


class FakeServerHost(abc.ServerHost):

    port = 1234
    auth_token = 'some_auth_token'
    user_agent_name = 'Testing-Agent'

    def port(self):
        """Specify the port to bind the listening socket to."""
        return self.port

    def contrib_auth_token(self):
        return self.auth_token

    def user_agent(self):
        return self.user_agent_name

    def log_exception(self, exc):
        """Log the exception."""
        self.logged_exc = exc

    def log(self, message):
        try:
            self.logged.append(message)
        except AttributeError:
            self.logged = [message]


class TestCase(unittest.TestCase):

    @classmethod
    def tearDownClass(cls):
        session = abc.session()
        session.close()
        abc.session = abc._session_factory()
        super().tearDownClass()

    def run_awaitable(self, coroutine, *, loop=None):
        if loop is None:
            loop = asyncio.new_event_loop()
            self.addCleanup(loop.close)
        return loop.run_until_complete(coroutine)

    def noException(self, coroutine):
        # Shouldn't raise any exception.
        return self.run_awaitable(coroutine)
