"""Implement a server to check if a contribution is covered by a CLA(s)."""
import asyncio
import http

from aiohttp import web

from . import abc as ni_abc
from . import CLAHost
from . import ContribHost
from . import ServerHost


def handler(create_client, server, cla_records):
    """Create a closure to handle requests from the contribution host."""
    async def respond(request):
        """Handle a webhook trigger from the contribution host."""
        async with create_client() as client:
            try:
                contribution = await ContribHost.process(server, request)
                usernames = await contribution.usernames(client)
                server.log("Usernames: " + str(usernames))
                cla_status = await cla_records.check(client, usernames)
                server.log("CLA status: " + str(cla_status))
                # With a work queue, one could make the updating of the
                # contribution a work item and return an HTTP 202 response.
                await contribution.update(client, cla_status)
                return web.Response(status=http.HTTPStatus.OK)
            except ni_abc.ResponseExit as exc:
                return exc.response
            except Exception as exc:
                server.log_exception(exc)
                return web.Response(
                        status=http.HTTPStatus.INTERNAL_SERVER_ERROR)

    return respond


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    app = web.Application(loop=loop)
    server = ServerHost()
    cla_records = CLAHost(server)
    app.router.add_route(*ContribHost.route,
                         handler(lambda: aiohttp.ClientSession(loop=loop), server, cla_records))
    web.run_app(app, port=server.port())
