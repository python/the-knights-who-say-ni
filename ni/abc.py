import abc
import enum
import http
from typing import AbstractSet, Any, Optional, Tuple

# ONLY third-party libraries which won't break the abstraction promise may be
# imported.
import aiohttp
from aiohttp import web


class ResponseExit(Exception):

    """Exception to raise when the current request should immediately exit."""

    def __init__(self, *args: Any, status: http.HTTPStatus,
                 text: str = None) -> None:
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
    def port(self) -> int:
        """Specify the port to bind the listening socket to."""
        raise NotImplementedError

    @abc.abstractmethod
    def contrib_auth_token(self) -> str:
        """Return the authorization token for the contribution host."""
        raise NotImplementedError

    @abc.abstractmethod
    def contrib_secret(self) -> str:
        """Return the secret for the contribution host."""

    @abc.abstractmethod
    def user_agent(self) -> Optional[str]:
        """Return the HTTP User-Agent string, or None."""

    @abc.abstractmethod
    def log_exception(self, exc: BaseException) -> None:
        """Log the exception."""

    @abc.abstractmethod
    def log(self, message: str) -> None:
        """Log the message."""

    @abc.abstractmethod
    def trusted_users(self) -> AbstractSet[str]:
        """Return a list of trusted users.

        Trusted users will not be checked for CLA.
        """
        return frozenset()


class ContribHost(abc.ABC):

    """Abstract base class for the contribution/pull request platform."""

    @property
    @abc.abstractmethod
    def route(self) -> Tuple[str, str]:
        return '*', '/'  # pragma: no cover

    @classmethod
    @abc.abstractmethod
    async def process(cls, server: ServerHost,
                      request: web.Request,
                      client: aiohttp.ClientSession) -> "ContribHost":
        """Process a request into a contribution."""
        # This method exists because __init__() cannot be a coroutine.
        raise ResponseExit(status=http.HTTPStatus.NOT_IMPLEMENTED)  # pragma: no cover

    @abc.abstractmethod
    async def usernames(self) -> AbstractSet[str]:
        """Return an iterable of all the contributors' usernames."""
        return frozenset()  # pragma: no cover

    @abc.abstractmethod
    async def update(self, status: Status) -> None:
        """Update the contribution with the status of CLA coverage."""


class CLAHost(abc.ABC):

    """Abstract base class for the CLA records platform."""

    @abc.abstractmethod
    async def check(self, client: aiohttp.ClientSession,
                    usernames: AbstractSet[str]) -> Status:
        """Check if all of the specified usernames have signed the CLA."""
        # While it would technically share more specific information if a
        # mapping of {username: Status} was returned, the vast majority of
        # cases will be for a single user and thus not worth the added
        # complexity to need to worry about it.
        return Status.username_not_found  # pragma: no cover
