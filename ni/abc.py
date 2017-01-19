import abc
import asyncio
import http

import aiohttp
from aiohttp import web

import enum


class ResponseExit(Exception):

    """Exception to raise when the current request should immediately exit."""

    def __init__(self, *args, status, text=None):
        super().__init__(*args)
        self.response = web.Response(status=status.value, text=text)


class Status(enum.Enum):

    """The CLA status of the contribution."""

    signed = 1
    not_signed = 2
    username_not_found = 3


class ServerHost(abc.ABC):

    """Abstract base class for the server hosting platform."""

    @abc.abstractmethod
    def port(self):
        """Specify the port to bind the listening socket to."""
        raise NotImplementedError

    @abc.abstractmethod
    def contrib_auth_token(self):
        """Return the authorization token for the contribution host."""
        raise NotImplementedError

    @abc.abstractmethod
    def user_agent(self):
        """Return the HTTP User-Agent string, or None."""

    @abc.abstractmethod
    def log_exception(self, exc):
        """Log the exception."""

    @abc.abstractmethod
    def log(self, message):
        """Log the message."""


class ContribHost(abc.ABC):

    """Abstract base class for the contribution/pull request platform."""

    @property
    @abc.abstractmethod
    def route(self):
        return '*', '/'  # pragma: no cover

    @classmethod
    @abc.abstractmethod
    async def process(cls, server, request):
        """Process a request into a contribution."""
        # This method exists because __init__() cannot be a coroutine.
        raise ResponseExit(status=http.HTTPStatus.NOT_IMPLEMENTED)  # pragma: no cover

    @abc.abstractmethod
    async def usernames(self, client):
        """Return an iterable of all the contributors' usernames."""
        return []  # pragma: no cover

    @abc.abstractmethod
    async def update(self, client, status):
        """Update the contribution with the status of CLA coverage."""


class CLAHost(abc.ABC):

    """Abstract base class for the CLA records platform."""

    @abc.abstractmethod
    async def check(self, client, usernames):
        """Check if all of the specified usernames have signed the CLA."""
        # While it would technically share more specific information if a
        # mapping of {username: Status} was returned, the vast majority of
        # cases will be for a single user and thus not worth the added
        # complexity to need to worry about it.
        return Status.USERNAME_NOT_FOUND  # pragma: no cover
