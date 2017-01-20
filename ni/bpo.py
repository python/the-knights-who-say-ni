from http import client
import json
from typing import AbstractSet

import aiohttp

from . import abc as ni_abc


class Host(ni_abc.CLAHost):

    """CLA record hosting at bugs.python.org."""

    def __init__(self, server: ni_abc.ServerHost) -> None:
        self.server = server

    async def check(self, aio_client: aiohttp.ClientSession,
                    usernames: AbstractSet[str]) -> ni_abc.Status:
        base_url = "http://bugs.python.org/user?@template=clacheck&github_names="
        url = base_url + ','.join(usernames)
        self.server.log("Checking CLA status: " + url)
        async with aio_client.get(url) as response:
            if response.status >= 300:
                msg = 'unexpected response for {!r}: {}'.format(response.url,
                                                                response.status)
                raise client.HTTPException(msg)
            # Explicitly decode JSON as b.p.o doesn't set the content-type as
            # `application/json`.
            results = json.loads(await response.text())
        self.server.log("Raw CLA status: " + str(results))
        status_results = [results[k] for k in results.keys() if k in usernames]
        self.server.log("Filtered CLA status: " + str(status_results))
        if len(status_results) != len(usernames):
            raise ValueError("# of usernames don't match # of results "
                             "({} != {})".format(len(usernames), len(status_results)))
        elif any(x not in (True, False, None) for x in status_results):
            raise TypeError("unexpected value in " + str(status_results))

        if all(status_results):
            return ni_abc.Status.signed
        elif any(value is None for value in status_results):
            return ni_abc.Status.username_not_found
        else:
            return ni_abc.Status.not_signed
