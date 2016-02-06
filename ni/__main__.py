"""Implement a server to check if a contribution is covered by a CLA(s)."""
from aiohttp import web

from . import ContribHost
from . import ServerHost
from . import CLAHost


async def webhook(request: web.Request) -> web.StreamResponse:
    """Handle a webhook trigger from the contribution host."""
    # https://developer.github.com/webhooks/creating/#content-type
    if request.content_type != 'application/json':
        msg = 'can only accept application/json, not {}'.format(request.content_type)
        return web.Response(status=415, text=msg)
    # aiohttp doesn't document the constructor for web.Request, so its use
    # is abstracted out to make testing easier.
    payload = await request.json()
    contribution = ContribHost.process(payload)
    if contribution is None:
        return ContribHost.nothing_to_do()
    usernames = await contribution.usernames()
    cla_records = CLAHost()
    cla_status = await cla_records.check(usernames)
    return (await contribution.update(cla_status))


if __name__ == '__main__':
    app = web.Application()
    server = ServerHost()
    app.router.add_route(*ContribHost.route, webhook)
    web.run_app(app, port=server.port())