import abc
import asyncio
import http

import aiohttp
from aiohttp import web

import enum


loop = asyncio.get_event_loop


def _session_factory():
    """Create a closure to create/cache a client session.

    A single session should be used for the life of the server, but creating it
    should be minimized as it will trigger the creation of an event loop which
    is not necessary during testing.
    """
    _session = None
    def session():
        nonlocal _session
        if _session is None:
            _session = aiohttp.ClientSession(loop=loop())
        return _session

    return session

session = _session_factory()


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
    def log(self, exc):
        """Log the exception."""


class ContribHost(abc.ABC):

    """Abstract base class for the contribution/pull request platform."""

    @property
    @abc.abstractstaticmethod
    def route():
        return '*', '/'  # pragma: no cover

    @abc.abstractclassmethod
    async def process(self, server, request):
        """Process a request into a contribution."""
        # This method exists because __init__() cannot be a coroutine.
        raise ResponseExit(status=http.HTTPStatus.NOT_IMPLEMENTED)  # pragma: no cover

    @abc.abstractmethod
    async def usernames(self):
        """Return an iterable of all the contributors' usernames."""
        return []  # pragma: no cover

    @abc.abstractmethod
    async def update(self, status):
        """Update the contribution with the status of CLA coverage."""


class CLAHost(abc.ABC):

    """Abstract base class for the CLA records platform."""

    @abc.abstractmethod
    async def check(self, usernames):
        """Check if all of the specified usernames have signed the CLA."""
        # While it would technically share more specific information if a
        # mapping of {username: Status} was returned, the vast majority of
        # cases will be for a single user and thus not worth the added
        # complexity to need to worry about it.
        return Status.USERNAME_NOT_FOUND  # pragma: no cover
