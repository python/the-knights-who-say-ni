import enum
import http
from http import client
import operator
import typing as t
from urllib import parse

import aiohttp
from aiohttp import hdrs
from aiohttp import web

from . import abc


LABEL_PREFIX = 'CLA: '
CLA_OK = LABEL_PREFIX + '☑'
NO_CLA = LABEL_PREFIX + '☐'


@enum.unique
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


JSONType = t.Union[str, int, float, bool, None, t.Dict[str, t.Any],
                   t.List[t.Any]]


class Host(abc.ContribHost):

    """Implement a webhook for GitHub pull requests."""

    route = 'POST', '/github'

    _useful_actions =  {PullRequestEvent.opened.value,
                        PullRequestEvent.unlabeled.value,
                        PullRequestEvent.synchronize.value}

    def __init__(self, event: PullRequestEvent, request: JSONType):
        """Represent a contribution."""
        self.event = event
        self.request = request

    @classmethod
    async def process(cls, request):
        """Process the pull request."""
        # https://developer.github.com/webhooks/creating/#content-type
        if request.content_type != 'application/json':
            msg = ('can only accept application/json, '
                   'not {}').format(request.content_type)
            raise abc.ResponseExit(
                    status=http.HTTPStatus.UNSUPPORTED_MEDIA_TYPE, text=msg)

        payload = await request.json()
        if 'zen' in payload:
            # A ping event; nothing to do.
            # https://developer.github.com/webhooks/#ping-event
            raise abc.ResponseExit(status=http.HTTPStatus.NO_CONTENT)
        elif payload['action'] not in cls._useful_actions:
            raise abc.ResponseExit(status=http.HTTPStatus.NO_CONTENT)
        elif payload['action'] == PullRequestEvent.opened.value:
            return cls(PullRequestEvent.opened, payload)
        elif payload['action'] == PullRequestEvent.unlabeled.value:
            label = payload['label']['name']
            if not label.startswith(LABEL_PREFIX):
                raise abc.ResponseExit(status=http.HTTPStatus.NO_CONTENT)
            return cls(PullRequestEvent.unlabeled, payload)
        elif payload['action'] == PullRequestEvent.synchronize.value:
            return cls(PullRequestEvent.synchronize, payload)
        else:  # pragma: no cover
            # Should never happen.
            msg = "don't know how to handle a {!r} event".format(
                payload['action'])
            raise TypeError(msg)

    @staticmethod
    def check_response(response: web.Response):
        if response.status >= 300:
            msg = 'unexpected response: {}'.format(response.status)
            raise client.HTTPException(msg)

    async def get(self, url: str) -> JSONType:
        """Make a GET request for some JSON data.

        Abstracted out for easy testing w/o requiring internet access.
        """
        async with abc.session().get(url) as response:
            self.check_response(response)
            return (await response.json())

    async def post(self, url: str, payload: JSONType) -> None:
        """Make a POST request with JSON data to a URL."""
        encoded_json = json.dumps(payload).encode('utf-8')
        header = {hdrs.CONTENT_TYPE: 'application/json; charset=utf-8'}
        async with abc.session().post(url, data=encoded_json, headers=header) as response:
            self.check_response(response)

    async def delete(self, url: str) -> None:
        """Make a DELETE request to a URL."""
        async with abc.session().delete(url) as response:
            self.check_response(response)

    async def usernames(self):
        """Return an iterable with all of the contributors' usernames."""
        pull_request = self.request['pull_request']
        # Start with the author of the pull request.
        logins = {pull_request['user']['login']}
        # Fetch the commit data for the pull request.
        commits = await self.get(pull_request['commits_url'])
        # For each commit, get the author and committer.
        for commit in commits:
            logins.add(commit['author']['login'])
            logins.add(commit['committer']['login'])
        return frozenset(logins)

    async def labels_url(self, label=None):
        """Construct the URL to the label."""
        if not hasattr(self, '_labels_url'):
            issue_url = self.request['pull_request']['issue_url']
            issue_data = await self.get(issue_url)
            self._labels_url = issue_data['labels_url']
        quoted_label = ''
        if label is not None:
            quoted_label = '/' + parse.quote(label)
        mapping = {'/name': quoted_label}
        return self._labels_url.format_map(mapping)

    async def set_label(self, status: abc.Status) -> str:
        """Set the label on the pull request based on the status of the CLA."""
        labels_url = await self.labels_url()
        if status == abc.Status.signed:
            await self.post(labels_url, [CLA_OK])
            return CLA_OK
        else:
            await self.post(labels_url, [NO_CLA])
            return NO_CLA

    async def remove_labels(self) -> t.Container[str]:
        """Remove any CLA-related labels from the pull request."""
        removed = set()
        labels_url = await self.labels_url()
        all_labels = map(operator.itemgetter('name'),
                         await self.get(labels_url))
        for cla_label in (x for x in all_labels if x.startswith(LABEL_PREFIX)):
            deletion_url = await self.labels_url(cla_label)
            await self.delete(deletion_url)
            removed.add(cla_label)
        return frozenset(removed)

    async def comment(self, status: abc.Status):
        """Add an appropriate comment relating to the CLA status."""
        if status == abc.Status.signed:
            return
        # XXX not_signed
        # XXX username_not_found

    async def update(self, status):
        if self.event == PullRequestEvent.opened:
            await self.set_label(status)
            await self.comment(status)
        elif self.event == PullRequestEvent.unlabeled:
            # The assumption is that a PR will almost always go from no CLA to
            # being cleared, so don't bug the user with what will probably
            # amount to a repeated message about lacking a CLA.
            await self.set_label(status)
        elif self.event == PullRequestEvent.synchronize:
            current_label = await self.current_label()
            if status == abc.Status.signed:
                if current_label != CLA_OK:
                    await self.remove_labels()
            elif current_label != NO_CLA:
                    await self.remove_labels()
                    # Since there is a chance a new person was added to a PR
                    # which caused the change in status, a comment on how to
                    # resolve the CLA issue is probably called for.
                    await self.comment(status)
        else:  # pragma: no cover
            # Should never be reached.
            msg = 'do not know how to update a PR for {}'.format(self.event)
            raise RunimeError(msg)
