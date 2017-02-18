import enum
import http
from http import client
import json
import operator
import random
from typing import AbstractSet, Any, Dict, Optional
from urllib import parse

import aiohttp
from aiohttp import hdrs, web

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

Thanks again to your contribution and we look forward to looking at it!
"""

NO_CLA_BODY = """Unfortunately our records indicate you have not signed the CLA. \
For legal reasons we need you to sign this before we can look at your \
contribution. Please follow these steps to rectify the issue:

1. Sign the [PSF contributor agreement](https://www.python.org/psf/contrib/contrib-form/). \
The "bugs.python.org username" requested by the form is the "Login name" field under \
"Your Details" on [bugs.python.org](https://bugs.python.org/)
2. **Wait at least one US business day** and then check the "Contributor form received"
entry under "Your Details" to see if your account has been marked as having signed the CLA \
(the delay is due to a person having to manually check your signed CLA)
3. Reply here saying you have completed the above steps
"""

NO_CLA_BODY_EASTEREGG = NO_CLA_BODY + """

We also demand... [A SHRUBBERY!](https://www.youtube.com/watch?v=zIV4poUZAQo)
"""

NO_USERNAME_BODY = """Unfortunately we couldn't find an account corresponding \
to your GitHub username on [bugs.python.org](http://bugs.python.org/) \
(b.p.o) to verify you have signed the CLA. This is necessary for legal reasons \
before we can look at your contribution. Please follow these steps to help \
rectify the issue:

1. If you don't have an account on b.p.o, please [create one](http://bugs.python.org/user?@template=register)
2. Make sure your GitHub username is listed in \
["Your Details" at b.p.o](https://cloud.githubusercontent.com/assets/2680980/22867185/d3aedcf8-f137-11e6-8469-d5f7861a1073.png)
3. If you have not already done so, please sign the \
[PSF contributor agreement](https://www.python.org/psf/contrib/contrib-form/)
4. If you just signed the CLA, please **wait at least one US business day** and then check "Your Details" on \
[bugs.python.org](https://bugs.python.org/) to see if your account has been \
marked as having signed the CLA \
(the delay is due to a person having to manually check your signed CLA)
5. Reply here saying you have completed the above steps
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

    def __init__(self, server: ni_abc.ServerHost, event: PullRequestEvent,
                 request: JSONDict) -> None:
        """Represent a contribution."""
        self.server = server
        self.event = event
        self.request = request

    @classmethod
    async def process(cls, server: ni_abc.ServerHost,
                      request: web.Request) -> "Host":
        """Process the pull request."""
        # https://developer.github.com/webhooks/creating/#content-type
        if request.content_type != 'application/json':
            msg = ('can only accept application/json, '
                   'not {}').format(request.content_type)
            raise ni_abc.ResponseExit(
                    status=http.HTTPStatus.UNSUPPORTED_MEDIA_TYPE, text=msg)

        payload = await request.json()
        if 'zen' in payload:
            # A ping event; nothing to do.
            # https://developer.github.com/webhooks/#ping-event
            raise ni_abc.ResponseExit(status=http.HTTPStatus.OK)
        elif payload['action'] not in cls._useful_actions:
            raise ni_abc.ResponseExit(status=http.HTTPStatus.NO_CONTENT)
        elif payload['action'] in {PullRequestEvent.opened.value, PullRequestEvent.synchronize.value}:
            return cls(server, PullRequestEvent(payload['action']), payload)
        elif payload['action'] == PullRequestEvent.unlabeled.value:
            label = payload['label']['name']
            if not label.startswith(LABEL_PREFIX):
                raise ni_abc.ResponseExit(status=http.HTTPStatus.NO_CONTENT)
            return cls(server, PullRequestEvent.unlabeled, payload)
        else:  # pragma: no cover
            # Should never happen.
            msg = "don't know how to handle a {!r} event".format(
                payload['action'])
            raise TypeError(msg)

    @staticmethod
    def check_response(response: web.Response) -> None:
        if response.status >= 300:
            msg = 'unexpected response for {!r}: {}'.format(response.url,
                                                            response.status)
            raise client.HTTPException(msg)

    def auth_header(self) -> Dict[str, str]:
        return {'Authorization': 'token ' + self.server.contrib_auth_token()}

    async def get(self, client: aiohttp.ClientSession, url: str) -> JSON:
        """Make a GET request for some JSON data.

        Abstracted out for easy testing w/o requiring internet access.
        """
        headers = self.auth_header()
        async with client.get(url, headers=headers) as response:
            self.check_response(response)
            return (await response.json())

    async def post(self, client: aiohttp.ClientSession, url: str,
                   payload: JSON) -> None:
        """Make a POST request with JSON data to a URL."""
        encoding = 'utf-8'
        encoded_json = json.dumps(payload).encode(encoding)
        headers = {hdrs.CONTENT_TYPE: 'application/json; charset=' + encoding}
        user_agent = self.server.user_agent()
        if user_agent:
            headers[hdrs.USER_AGENT] = user_agent
        headers.update(self.auth_header())
        post_manager = client.post(url, data=encoded_json,
                                          headers=headers)
        async with post_manager as response:
            self.check_response(response)

    async def delete(self, client: aiohttp.ClientSession,
                     url: str) -> None:
        """Make a DELETE request to a URL."""
        headers = self.auth_header()
        async with client.delete(url, headers=headers) as response:
            self.check_response(response)

    async def usernames(self,
                        client: aiohttp.ClientSession) -> AbstractSet[str]:
        """Return an iterable with all of the contributors' usernames."""
        pull_request = self.request['pull_request']
        # Start with the author of the pull request.
        logins = {pull_request['user']['login']}
        # Fetch the commit data for the pull request.
        commits = await self.get(client, pull_request['commits_url'])
        # For each commit, get the author and committer.
        for commit in commits:
            author = commit['author']
            # When the author is missing there seems to typically be a
            # matching commit that **does** specify the author. (issue #56)
            if author is not None:
                author_login = author['login']
                if commit['commit']['author']['email'].lower() == GITHUB_EMAIL:
                    self.server.log("Ignoring GitHub-managed username: "
                                    + author_login)
                else:
                    logins.add(author_login)

            committer = commit['committer']
            if committer is not None:
                committer_login = committer['login']
                if commit['commit']['committer']['email'].lower() == GITHUB_EMAIL:
                    self.server.log("Ignoring GitHub-managed username: "
                                    + committer_login)
                else:
                    logins.add(committer_login)
        return frozenset(logins)

    async def labels_url(self, client: aiohttp.ClientSession,
                         label: str = None) -> str:
        """Construct the URL to the label."""
        if not hasattr(self, '_labels_url'):
            issue_url = self.request['pull_request']['issue_url']
            issue_data = await self.get(client, issue_url)
            self._labels_url = issue_data['labels_url']
        quoted_label = ''
        if label is not None:
            quoted_label = '/' + parse.quote(label)
        mapping = {'/name': quoted_label}
        return self._labels_url.format_map(mapping)

    async def current_label(self,
                            client: aiohttp.ClientSession) -> Optional[str]:
        """Return the current CLA-related label."""
        labels_url = await self.labels_url(client)
        all_labels = map(operator.itemgetter('name'),
                         await self.get(client, labels_url))
        cla_labels = [x for x in all_labels if x.startswith(LABEL_PREFIX)]
        cla_labels.sort()
        return cla_labels[0] if len(cla_labels) > 0 else None

    async def set_label(self, client: aiohttp.ClientSession,
                        status: ni_abc.Status) -> str:
        """Set the label on the pull request based on the status of the CLA."""
        labels_url = await self.labels_url(client)
        if status == ni_abc.Status.signed:
            await self.post(client, labels_url, [CLA_OK])
            return CLA_OK
        else:
            await self.post(client, labels_url, [NO_CLA])
            return NO_CLA

    async def remove_label(self, client: aiohttp.ClientSession) -> Optional[str]:
        """Remove any CLA-related labels from the pull request."""
        cla_label = await self.current_label(client)
        if cla_label is None:
            return None
        deletion_url = await self.labels_url(client, cla_label)
        await self.delete(client, deletion_url)
        return cla_label

    async def comment(self, client: aiohttp.ClientSession,
                      status: ni_abc.Status) -> Optional[str]:
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
        await self.post(client, comments_url, {'body': message})
        return message

    async def update(self, client: aiohttp.ClientSession,
                     status: ni_abc.Status) -> None:
        if self.event == PullRequestEvent.opened:
            await self.set_label(client, status)
            await self.comment(client, status)
        elif self.event == PullRequestEvent.unlabeled:
            # The assumption is that a PR will almost always go from no CLA to
            # being cleared, so don't bug the user with what will probably
            # amount to a repeated message about lacking a CLA.
            await self.set_label(client, status)
        elif self.event == PullRequestEvent.synchronize:
            current_label = await self.current_label(client)
            if status == ni_abc.Status.signed:
                if current_label != CLA_OK:
                    await self.remove_label(client)
            elif current_label != NO_CLA:
                    await self.remove_label(client)
                    # Since there is a chance a new person was added to a PR
                    # which caused the change in status, a comment on how to
                    # resolve the CLA issue is probably called for.
                    await self.comment(client, status)
        else:  # pragma: no cover
            # Should never be reached.
            msg = 'do not know how to update a PR for {}'.format(self.event)
            raise RuntimeError(msg)
