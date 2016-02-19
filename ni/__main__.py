"""Implement a server to check if a contribution is covered by a CLA(s)."""
import aiohttp
from aiohttp import web

from . import abc
from . import ContribHost
from . import ServerHost
from . import CLAHost


class Handler:

    """Handle requests from the contribution host."""

    def __init__(self, server: ServerHost, cla_records: CLAHost,
                 session: aiohttp.ClientSession):
        self.server = server
        self.cla_records = cla_records
        self.session = session

    async def respond(request: web.Request) -> web.StreamResponse:  # XXX untested
        """Handle a webhook trigger from the contribution host."""
        try:
            contribution = ContribHost.process(request, session=session)
            usernames = await contribution.usernames()
            cla_status = await self.cla_records.check(usernames)  # XXX blocked on b.p.o.
            # With a work queue, one could make the updating of the
            # contribution a work item and return an HTTP 202 response.
            return (await contribution.update(cla_status))  # XXX not implemented
        except abc.ResponseExit as exc:
            return exc.response
        except Exception as exc:
            self.server.log(exc)
            return web.Response(
                    status=http.HTTPStatus.INTERNAL_SERVER_ERROR.value)


if __name__ == '__main__':
    app = web.Application()
    session = aiohttp.ClientSession(loop=app.loop)
    server = ServerHost()
    cla_records = CLAHost()
    handler = Handler(server, cla_records, session)
    app.router.add_route(*ContribHost.route, handler.respond)
    web.run_app(app, port=server.port())
