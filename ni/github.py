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

    @classmethod
    async def process(cls, request):
        """Process the pull request.

        Only need to process opened, unlabeled, synchronized events.
        """
        if request['action'] not in cls._acceptable_actions:
            return None
        # XXX opened
        # XXX unlabeled
        # XXX synchronize

    @staticmethod
    def nothing_to_do() -> web.StreamResponse:
        """Return a response saying nothing is needed."""
        # XXX what does GitHub want as a response?
        raise NotImplementedError