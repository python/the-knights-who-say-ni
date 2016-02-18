import abc
import http
import typing as t

from aiohttp import web

import enum


class ResponseExit(web.Response, Exception):

    """Exception to raise when the current request should immediately exit."""

    def __init__(self, *args, status: http.HTTPStatus, text: str=None):
        super().__init__(*args)
        self.response = web.Response(status=status.value, text=text)


class Status(enum.Enum):

    """The CLA status of the contribution."""

    SIGNED = 1
    NOT_SIGNED = 2
    USERNAME_NOT_FOUND = 3


class ServerHost(metaclass=abc.ABCMeta):

    """Abstract base class for the server hosting platform."""

    @abc.abstractmethod
    def port(self) -> int:
        """Specify the port to bind the listening socket to."""
        raise NotImplementedError

    def log(self, exc: Exception):
        """Log the exception."""


class ContribHost(metaclass=abc.ABCMeta):

    """Abstract base class for the contribution/pull request platform."""

    @property
    @abc.abstractstaticmethod
    def route() -> t.Tuple[str, str]:
        return '*', '/'  # pragma: no cover

    @abc.abstractclassmethod
    async def process(self, request: web.Request) -> 'ContribHost':
        """Process a request into a contribution."""
        # Method exists because __init__() cannot be a coroutine.
        raise ResponseExit(status=http.HTTPStatus.NOT_IMPLEMENTED)  # pragma: no cover

    @abc.abstractmethod
    async def usernames(self) -> t.Iterable[str]:
        """Return an iterable of all the contributors' usernames."""
        return []  # pragma: no cover

    @abc.abstractmethod
    async def update(self, status: Status) -> web.StreamResponse:
        return web.Response(status=501)  # pragma: no cover


class CLAHost(metaclass=abc.ABCMeta):

    """Abstract base class for the CLA records platform."""

    @abc.abstractmethod
    async def check(self, usernames: t.Iterable[str]) -> Status:
        """Check if all of the specified usernames have signed the CLA."""
        return Status.USERNAME_NOT_FOUND  # pragma: no cover
