import enum

from aiohttp import web

from . import abc


enum.unique
class PullRequestEvent(enum.Enum):
    # https://developer.github.com/v3/activity/events/types/#pullrequestevent
    assigned = "assigned"
    unassigned = "unassigned"
    labeled = "labeled"
    unlabeled = "unlabeled"
    opened = "opened"
    closed = "closed"
    reopened = "reopened"
    synchronize = "synchronize"


class Host(abc.ContribHost):

    """Implement a webhook for GitHub pull requests."""

    route = 'POST', '/github'

    _acceptable_actions =  {PullRequestEvent.opened.value,
                            PullRequestEvent.unlabeled.value,
                            PullRequestEvent.synchronize.value}

    def __init__(self, request):
        self.request = request

    @classmethod
    async def process(cls, request):
        """Process the pull request.

        Only need to process opened, unlabeled, synchronized events.
        """
        if 'zen' in request:
            # A ping event; nothing to do.
            # https://developer.github.com/webhooks/#ping-event
            return None
        elif request['action'] not in cls._acceptable_actions:
            return None
        # XXX opened
        # XXX unlabeled; might not care based on who the 'sender' is.
        # XXX synchronize

    @staticmethod
    def nothing_to_do() -> web.StreamResponse:
        """Return a response saying nothing is needed."""
        # XXX what does GitHub want as a response?
        raise NotImplementedError

    async def usernames(self):
        """Return an iterable with all of the contributors' usernames."""
        # XXX
        return []    # pragma: no cover

    async def update(self, status):
        # XXX
        return web.Response(status=501)    # pragma: no cover