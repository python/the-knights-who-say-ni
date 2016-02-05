import abc
import typing as t

from aiohttp import web

import enum


class Status(enum.Enum):
    SIGNED = 1
    NOT_SIGNED = 2
    MISSING_USERNAME = 3


class ServerHost(metaclass=abc.ABCMeta):

    """Abstract base class for the server hosting platform."""

    @abc.abstractmethod
    def port(self) -> int:
        """Specify the port to bind the listening socket to."""
        raise NotImplementedError


class ContribHost(metaclass=abc.ABCMeta):

    """Abstract base class for the contribution/pull request platform."""

    @property
    @abc.abstractstaticmethod
    def route() -> t.Tuple[str, str]:
        return '*', '/'  # pragma: no cover

    @abc.abstractclassmethod
    async def process(cls, request: t.Any) -> t.Optional['ContribHost']:
        """Process a request, returning None if there's nothing to do."""

    @abc.abstractstaticmethod
    def nothing_to_do() -> web.StreamResponse:
        """Respond to the contribution, signaling there's nothing to do."""
        return web.Response(status=501)    # pragma: no cover

    @abc.abstractmethod
    async def usernames(self) -> t.Iterable[str]:
        """Return an iterable with all of the contributors' usernames."""
        return []    # pragma: no cover

    @abc.abstractmethod
    async def update(self, status: Status) -> web.StreamResponse:
        return web.Response(status=501)    # pragma: no cover


class CLAHost(metaclass=abc.ABCMeta):

    """Abstract base class for the CLA records platform."""

    @abc.abstractmethod
    async def check(self, usernames: t.Iterable[str]) -> Status:
        """Check if all of the specified usernames have signed the CLA."""
        return Status.MISSING_USERNAME    # pragma: no cover