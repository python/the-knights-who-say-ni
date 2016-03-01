import asyncio
import unittest


# Inheriting from web.Request is bad as the docs explicitly say not to create
# instances manually. To work around that this faked request is provided.
# http://aiohttp.readthedocs.org/en/stable/web_reference.html#aiohttp.web.Request
class FakeRequest:

    def __init__(self, payload={}, content_type='application/json'):
        self.content_type = content_type
        self._payload = payload

    async def json(self):
        return self._payload


class TestCase(unittest.TestCase):

    def run_awaitable(self, coroutine, *, loop=None):
        if loop is None:
            loop = asyncio.new_event_loop()
            self.addCleanup(loop.close)
        return loop.run_until_complete(coroutine)

    def noException(self, coroutine):
        # Shouldn't raise any exception.
        self.run_awaitable(coroutine)
