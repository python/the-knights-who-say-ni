import abc
import typing as t

from aiohttp import web


class ServerHost(metaclass=abc.ABCMeta):

    """Abstract base class for the server hosting platform."""

    @abc.abstractmethod
    def port(self) -> int:
        """Specify the port to bind the listening socket to."""


class ContribHost(metaclass=abc.ABCMeta):

    """Abstract base class for the contribution/pull request platform."""

    @property
    @abc.abstractstaticmethod
    def route() -> t.Tuple[str, str]:
        return '*', '/'

    @abc.abstractclassmethod
    async def process(cls, request: web.Request) -> t.Optional['ContribHost']:
        """Process a request, returning None if there's nothing to do."""
        return None

    @abc.abstractstaticmethod
    def nothing_to_do() -> web.StreamResponse:
        """Respond to the contribution, signaling there's nothing to do."""
        return web.StreamResponse()


class CLAHost(metaclass=abc.ABCMeta):

    """Abstract base class for the CLA records platform."""