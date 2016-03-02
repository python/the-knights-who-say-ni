"""Implement a server to check if a contribution is covered by a CLA(s)."""
import http

from aiohttp import web

from . import abc
from . import CLAHost
from . import ContribHost
from . import ServerHost


def handler(server, cla_records):
    """Create a closure to handle requests from the contribution host."""
    async def respond(request):
        """Handle a webhook trigger from the contribution host."""
        try:
            contribution = await ContribHost.process(request)
            usernames = await contribution.usernames()
            cla_status = await cla_records.check(usernames)  # XXX blocked on b.p.o.
            # With a work queue, one could make the updating of the
            # contribution a work item and return an HTTP 202 response.
            await contribution.update(cla_status)
            return web.Response(status=http.HTTPStatus.NO_CONTENT)
        except abc.ResponseExit as exc:
            return exc.response
        except Exception as exc:
            server.log(exc)
            return web.Response(
                    status=http.HTTPStatus.INTERNAL_SERVER_ERROR)

    return respond


if __name__ == '__main__':
    app = web.Application(loop=abc.loop())
    async def cleanup(app):
        await abc.session().close()
    app.on_cleanup.append(cleanup)
    server = ServerHost()
    cla_records = CLAHost()
    app.router.add_route(*ContribHost.route,
                         handler(server, cla_records))
    web.run_app(app, port=server.port())
