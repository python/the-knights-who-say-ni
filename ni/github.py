import enum
import typing as t

from aiohttp import web

from . import abc


LABEL_PREFIX = 'CLA: '
OK_CLA = LABEL_PREFIX + '✓'
NO_CLA = LABEL_PREFIX + '✗'


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

    def __init__(self, event: PullRequestEvent, request: t.Any):
        """Represent a contribution."""
        self.event = event
        self.request = request

    @classmethod
    def process(cls, request):
        """Process the pull request.

        Only need to process opened, unlabeled, synchronized events.
        """
        if 'zen' in request:
            # A ping event; nothing to do.
            # https://developer.github.com/webhooks/#ping-event
            return None
        elif request['action'] not in cls._acceptable_actions:
            return None
        elif request['action'] == PullRequestEvent.opened.value:
            return cls(PullRequestEvent.opened, request)
        elif request['action'] == PullRequestEvent.unlabeled.value:
            label = request['label']['name']
            if not label.startswith(LABEL_PREFIX):
                return None
            return cls(PullRequestEvent.unlabeled, request)
        elif request['action'] == PullRequestEvent.synchronize.value:
            return cls(PullRequestEvent.synchronize, request)
        else:  # pragma: no cover
            # Should never happen.
            msg = "don't know how to handle a {!r} event".format(
                request['action'])
            raise TypeError(msg)

    async def usernames(self):
        """Return an iterable with all of the contributors' usernames."""
        # XXX
        return []    # pragma: no cover

    async def update(self, status):
        # XXX
        return web.Response(status=501)    # pragma: no cover