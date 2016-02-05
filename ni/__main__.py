"""Implement a server to check if a contribution is covered by a CLA(s)."""
from aiohttp import web

from . import ContribHost
from . import ServerHost


async def webhook(request: web.Request) -> web.StreamResponse:
    """Handle a webhook trigger from the contribution host."""
    contribution = await ContribHost.process(request)
    if contribution is None:
        return ContribHost.nothing_to_do()
    # XXX do something; see README for outline


if __name__ == '__main__':
    app = web.Application()
    server = ServerHost()
    app.router.add_route(*ContribHost.route, webhook)
    web.run_app(app, port=server.port())