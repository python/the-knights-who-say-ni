import asyncio
import enum
import http
import random
from typing import AbstractSet, Any, Dict, Optional

import aiohttp
from aiohttp import web
from gidgethub.aiohttp import GitHubAPI
from gidgethub import sansio
import uritemplate

from . import abc as ni_abc

JSON = Any
JSONDict = Dict[str, Any]


LABEL_PREFIX = 'CLA '
CLA_OK = LABEL_PREFIX + 'signed'
NO_CLA = LABEL_PREFIX + 'not signed'
EASTEREGG_PROBABILITY = 0.01

NO_CLA_TEMPLATE = """Hello, and thanks for your contribution!

I'm a bot set up to make sure that the project can legally accept your \
contribution by verifying you have signed the \
[PSF contributor agreement](https://www.python.org/psf/contrib/contrib-form/) \
(CLA).

{body}

You can [check yourself](https://check-python-cla.herokuapp.com/) to see if the CLA has been received.

Thanks again for your contribution, we look forward to reviewing it!
"""

NO_CLA_BODY = """Our records indicate we have not received your CLA. \
For legal reasons we need you to sign this before we can look at your \
contribution. Please follow \
[the steps outlined in the CPython devguide](https://devguide.python.org/pullrequest/#licensing) \
to rectify this issue.

If you have recently signed the CLA, please wait at least one business day
before our records are updated.
"""

NO_CLA_BODY_EASTEREGG = NO_CLA_BODY + """

We also demand... [A SHRUBBERY!](https://www.youtube.com/watch?v=zIV4poUZAQo)
"""

NO_USERNAME_BODY = """Unfortunately we couldn't find an account corresponding \
to your GitHub username on [bugs.python.org](https://bugs.python.org/) \
(b.p.o) to verify you have signed the CLA (this might be simply due to a \
missing "GitHub Name" entry in your b.p.o account settings). This is necessary \
for legal reasons before we can look at your contribution. Please follow \
[the steps outlined in the CPython devguide](https://devguide.python.org/pullrequest/#licensing) \
to rectify this issue.
"""


GITHUB_EMAIL = 'noreply@github.com'.lower()  # Normalized for easy comparisons.


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


class Host(ni_abc.ContribHost):

    """Implement a webhook for GitHub pull requests."""

    route = 'POST', '/github'

    _useful_actions =  {PullRequestEvent.opened.value,
                        PullRequestEvent.unlabeled.value,
                        PullRequestEvent.synchronize.value}

    def __init__(self, server: ni_abc.ServerHost, client: aiohttp.ClientSession,
                 event: PullRequestEvent,
                 request: JSONDict) -> None:
        """Represent a contribution."""
        self.server = server
        self.event = event
        self.request = request
        self._gh = GitHubAPI(client, "the-knights-who-say-ni",
                             oauth_token=server.contrib_auth_token())

    @classmethod
    async def process(cls, server: ni_abc.ServerHost,
                      request: web.Request, client: aiohttp.ClientSession) -> "Host":
        """Process the pull request."""
        event = sansio.Event.from_http(request.headers,
                                       await request.read(),
                                       secret=server.contrib_secret())
        if event.event == "ping":
            # A ping event; nothing to do.
            # https://developer.github.com/webhooks/#ping-event
            raise ni_abc.ResponseExit(status=http.HTTPStatus.OK)
        elif event.event != "pull_request":
            # Only happens if GitHub is misconfigured to send the wrong events.
            raise TypeError(f"don't know how to handle a {event.event!r} event")
        elif event.data['action'] not in cls._useful_actions:
            raise ni_abc.ResponseExit(status=http.HTTPStatus.NO_CONTENT)
        elif event.data['action'] in {PullRequestEvent.opened.value, PullRequestEvent.synchronize.value}:
            if event.data['action'] == PullRequestEvent.opened.value:
                # GitHub is eventually consistent, so add a delay to wait for
                # the API to digest the new pull request.
                await asyncio.sleep(1)
            return cls(server, client, PullRequestEvent(event.data['action']),
                       event.data)
        elif event.data['action'] == PullRequestEvent.unlabeled.value:
            label = event.data['label']['name']
            if not label.startswith(LABEL_PREFIX):
                raise ni_abc.ResponseExit(status=http.HTTPStatus.NO_CONTENT)
            return cls(server, client, PullRequestEvent.unlabeled, event.data)
        else:  # pragma: no cover
            # Should never happen.
            raise TypeError(f"don't know how to handle a {event.data['action']!r} action")

    async def usernames(self) -> AbstractSet[str]:
        """Return an iterable with all of the contributors' usernames."""
        pull_request = self.request['pull_request']
        # Start with the author of the pull request.
        logins = {pull_request['user']['login']}
        # For each commit, get the author and committer.
        async for commit in self._gh.getiter(pull_request['commits_url']):
            author = commit['author']
            # When the author is missing there seems to typically be a
            # matching commit that **does** specify the author. (issue #56)
            if author:
                author_login = author.get('login')
                if commit['commit']['author']['email'].lower() == GITHUB_EMAIL:
                    self.server.log("Ignoring GitHub-managed username: "
                                    + author_login)
                else:
                    logins.add(author_login)

            committer = commit['committer']
            if committer:
                committer_login = committer.get('login')
                if commit['commit']['committer']['email'].lower() == GITHUB_EMAIL:
                    self.server.log("Ignoring GitHub-managed username: "
                                    + committer_login)
                else:
                    logins.add(committer_login)
        return frozenset(logins)

    async def labels_url(self, label: str = None) -> str:
        """Construct the URL to the label."""
        if not hasattr(self, '_labels_url'):
            issue_url = self.request['pull_request']['issue_url']
            issue_data = await self._gh.getitem(issue_url)
            self._labels_url = uritemplate.URITemplate(issue_data['labels_url'])
        return self._labels_url.expand(name=label)

    async def current_label(self) -> Optional[str]:
        """Return the current CLA-related label."""
        labels_url = await self.labels_url()
        all_labels = []
        async for label in self._gh.getiter(labels_url):
            all_labels.append(label['name'])
        cla_labels = [x for x in all_labels if x.startswith(LABEL_PREFIX)]
        cla_labels.sort()
        return cla_labels[0] if len(cla_labels) > 0 else None

    async def set_label(self, status: ni_abc.Status) -> str:
        """Set the label on the pull request based on the status of the CLA."""
        labels_url = await self.labels_url()
        if status == ni_abc.Status.signed:
            await self._gh.post(labels_url, data=[CLA_OK])
            return CLA_OK
        else:
            await self._gh.post(labels_url, data=[NO_CLA])
            return NO_CLA

    async def remove_label(self) -> Optional[str]:
        """Remove any CLA-related labels from the pull request."""
        cla_label = await self.current_label()
        if cla_label is None:
            return None
        deletion_url = await self.labels_url(cla_label)
        await self._gh.delete(deletion_url)
        return cla_label

    async def comment(self, status: ni_abc.Status) -> Optional[str]:
        """Add an appropriate comment relating to the CLA status."""
        comments_url = self.request['pull_request']['comments_url']
        if status == ni_abc.Status.signed:
            return None
        elif status == ni_abc.Status.not_signed:
            if random.random() < EASTEREGG_PROBABILITY:  # pragma: no cover
                message = NO_CLA_TEMPLATE.format(body=NO_CLA_BODY_EASTEREGG)
            else:
                message = NO_CLA_TEMPLATE.format(body=NO_CLA_BODY)
        elif status == ni_abc.Status.username_not_found:
            message = NO_CLA_TEMPLATE.format(body=NO_USERNAME_BODY)
        else:  # pragma: no cover
            # Should never be reached.
            raise TypeError("don't know how to handle {}".format(status))
        await self._gh.post(comments_url, data={'body': message})
        return message

    async def update(self, status: ni_abc.Status) -> None:
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
            if status == ni_abc.Status.signed:
                if current_label != CLA_OK:
                    await self.remove_label()
            elif current_label != NO_CLA:
                    await self.remove_label()
                    # Since there is a chance a new person was added to a PR
                    # which caused the change in status, a comment on how to
                    # resolve the CLA issue is probably called for.
                    await self.comment(status)
        else:  # pragma: no cover
            # Should never be reached.
            msg = 'do not know how to update a PR for {}'.format(self.event)
            raise RuntimeError(msg)
