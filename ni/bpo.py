from collections import defaultdict
from http import client
import json
from typing import AbstractSet, Mapping

import aiohttp

from . import abc as ni_abc


class Host(ni_abc.CLAHost):

    """CLA record hosting at bugs.python.org."""

    def __init__(self, server: ni_abc.ServerHost) -> None:
        self.server = server

    async def check(self, aio_client: aiohttp.ClientSession,
                    usernames: AbstractSet[str]) -> Mapping[ni_abc.Status, AbstractSet[str]]:
        base_url = "https://bugs.python.org/user?@template=clacheck&github_names="
        url = base_url + ','.join(usernames)
        self.server.log("Checking CLA status: " + url)
        async with aio_client.get(url) as response:
            if response.status >= 300:
                msg = f'unexpected response for {response.url!r}: {response.status}'
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

        failures = {
            None: ni_abc.Status.username_not_found,
            False: ni_abc.Status.not_signed,
        }
        problems = defaultdict(set)
        for username, result in results.items():
            if result:
                continue
            problems[failures[result]].add(username)

        return problems
