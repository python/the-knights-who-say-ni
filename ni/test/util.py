import asyncio
import json
import unittest
from typing import Dict, Optional, Tuple

import aiohttp
from aiohttp import web
from multidict import CIMultiDict

from .. import abc as ni_abc


class FakeRequest(web.Request):

    """Provide a base class for faking requests.

    Inheriting from web.Request is bad as the docs explicitly say not to create
    instances manually. To work around that this faked request is provided.
    http://aiohttp.readthedocs.org/en/stable/web_reference.html#aiohttp.web.Request
    """

    @property
    def content_type(self):
        return self._content_type

    @property
    def headers(self):
        return self._headers

    def __init__(self, payload={}, content_type='application/json'):
        self._content_type = content_type
        self._payload = payload
        self._headers = {"x-github-event": "pull_request",
                         "x-github-delivery": "12345",
                         "content-type": "application/json"}

    async def read(self):
        return json.dumps(self._payload).encode("utf-8")


class FakeResponse(web.Response):

    headers = CIMultiDict({
        "content-type": "application/json; charset=utf-8",
        "x-ratelimit-limit": "10",
        "x-ratelimit-remaining": "5",
        "x-ratelimit-reset": "1",
    })
    url = "test URL"

    def __init__(self, data=None, **kwargs):
        super().__init__(**kwargs)
        self._data = data

    async def json(self):
        return self._data

    async def text(self):
        return self._data

    async def read(self):
        return json.dumps(self._data).encode("utf-8")


class FakeSession(aiohttp.ClientSession):

    _connector = None

    def __init__(self, responses={}, response=None):
        self._responses: Dict[Tuple[str, str], FakeResponse] = {}
        for request, data in responses.items():
            self._responses[request] = FakeResponse(status=200, data=data)
        if response is not None:
            self.next_response = response

    def __call__(self):
        return self

    async def __aenter__(self):
        try:
            return self.next_response
        except AttributeError:
            return None

    async def __aexit__(self, exc_type, exc, tb):
        pass

    def request(self, method, url, headers=None, data=None):
        self.method = method
        self.url = url
        self.data = data
        try:
            self.next_response = self._responses[(method, url)]
        except KeyError:
            pass
        return self

    def get(self, url, headers=None):
        return self.request("GET", url, headers=headers)

    def post(self, url, data, headers):
        return self.request("POST", url, headers=headers, data=data)

    def delete(self, url, headers=None):
        return self.request("DELETE", url, headers=headers)


class FakeServerHost(ni_abc.ServerHost):

    _port = 1234
    auth_token = 'some_auth_token'
    secret: Optional[str] = None
    user_agent_name = 'Testing-Agent'
    trusted_usernames = ''

    def port(self):
        """Specify the port to bind the listening socket to."""
        return self._port

    def contrib_auth_token(self):
        return self.auth_token

    def contrib_secret(self):
        return self.secret

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

    def trusted_users(self):
        return frozenset(frozenset([trusted.strip().lower()
                for trusted in self.trusted_usernames.split(",")]))


class TestCase(unittest.TestCase):

    def run_awaitable(self, coroutine, *, loop=None):
        if loop is None:
            loop = asyncio.new_event_loop()
            self.addCleanup(loop.close)
        return loop.run_until_complete(coroutine)

    def noException(self, coroutine):
        # Shouldn't raise any exception.
        return self.run_awaitable(coroutine)
