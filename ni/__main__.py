"""Implement a server to check if a contribution is covered by a CLA(s)."""
import http

from typing import Awaitable, Callable

# ONLY third-party libraries that don't break the abstraction promise may be
# imported.
import aiohttp
from aiohttp import web

from . import abc as ni_abc
from . import CLAHost
from . import ContribHost
from . import ServerHost

import os
import sentry_sdk

sentry_sdk.init(os.environ.get("SENTRY_DSN"))


def handler(create_client: Callable[[], aiohttp.ClientSession], server: ni_abc.ServerHost,
            cla_records: ni_abc.CLAHost) -> Callable[[web.Request], Awaitable[web.Response]]:
    """Create a closure to handle requests from the contribution host."""
    async def respond(request: web.Request) -> web.Response:
        """Handle a webhook trigger from the contribution host."""
        async with create_client() as client:
            try:
                contribution = await ContribHost.process(server, request, client)
                usernames = await contribution.usernames()
                server.log("Usernames: " + str(usernames))
                trusted_users = server.trusted_users()
                usernames_to_check = usernames - trusted_users
                cla_status = await cla_records.check(client, usernames_to_check)
                server.log("CLA status: " + str(cla_status))
                # With a work queue, one could make the updating of the
                # contribution a work item and return an HTTP 202 response.
                await contribution.update(cla_status)
                return web.Response(status=http.HTTPStatus.OK)
            except ni_abc.ResponseExit as exc:
                return exc.response
            except Exception as exc:
                server.log_exception(exc)
                return web.Response(
                        status=http.HTTPStatus.INTERNAL_SERVER_ERROR)

    return respond


if __name__ == '__main__':
    app = web.Application()
    server = ServerHost()
    cla_records = CLAHost(server)
    app.router.add_route(*ContribHost.route,
                         handler(lambda: aiohttp.ClientSession(), server, cla_records))
    web.run_app(app, port=server.port())
