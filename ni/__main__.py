"""Implement a server to check if a contribution is covered by a CLA(s)."""
from aiohttp import web

from . import abc
from . import ContribHost
from . import ServerHost
from . import CLAHost


class Handler:

    """Handle requests from the contribution host."""

    def __init__(self, server: ServerHost, cla_records: CLAHost):
        self.server = server
        self.cla_records = cla_records

    async def respond(request: web.Request) -> web.StreamResponse:  # XXX untested
        """Handle a webhook trigger from the contribution host."""
        try:
            contribution = ContribHost.process(request)
            usernames = await contribution.usernames()  # XXX not implemented
            cla_status = await self.cla_records.check(usernames)  # XXX not implemented
            # With a background queue, could add update as work and return
            # HTTP 202.
            return (await contribution.update(cla_status))  # XXX not implemented
        except abc.ResponseExit as exc:
            return exc.response
        except Exception as exc:
            self.server.log(exc)
            return web.Response(
                    status=http.HTTPStatus.INTERNAL_SERVER_ERROR.value)


if __name__ == '__main__':
    server = ServerHost()
    cla_records = CLAHost()
    handler = Handler(server, cla_records)
    app = web.Application()
    app.router.add_route(*ContribHost.route, handler.respond)
    web.run_app(app, port=server.port())
