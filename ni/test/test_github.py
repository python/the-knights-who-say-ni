import asyncio
import unittest

from aiohttp import hdrs, web

from .. import abc
from .. import github


# Inheriting from web.Request is bad as the docs explicitly say not to create
# instances manually. To work around that this faked request is provided.
# http://aiohttp.readthedocs.org/en/stable/web_reference.html#aiohttp.web.Request
class FakeRequest:

    def __init__(self, payload={}, content_type='application/json'):
        self.content_type = content_type
        self._payload = payload

    async def json(self):
        return self._payload


class GitHubTests(unittest.TestCase):

    acceptable = {github.PullRequestEvent.opened,
                  github.PullRequestEvent.unlabeled,
                  github.PullRequestEvent.synchronize}

    def run_awaitable(self, coroutine):
        loop = asyncio.new_event_loop()
        self.addCleanup(loop.close)
        return loop.run_until_complete(coroutine)

    def test_bad_content_type(self):
        # Only accept 'application/json'.
        # https://developer.github.com/webhooks/creating/#content-type
        request = FakeRequest(content_type='application/x-www-form-urlencoded')
        with self.assertRaises(abc.ResponseExit) as cm:
            self.run_awaitable(github.Host.process(request))
        self.assertEqual(cm.exception.response.status, 415)

    def test_ping(self):
        # GitHub can ping a webhook to verify things are set up.
        # https://developer.github.com/webhooks/#ping-event
        payload = {'zen': 'something pithy'}
        with self.assertRaises(abc.ResponseExit) as cm:
            self.run_awaitable(github.Host.process(FakeRequest(payload)))
        self.assertEqual(cm.exception.response.status, 204)

    def test_process_skipping(self):
        # Only create a ContibHost object if the PR is opened, unlabeled, or
        # synchronized.
        for event in github.PullRequestEvent:
            if event in self.acceptable:
                continue
            payload = {'action': event.value}
            request = FakeRequest(payload)
            with self.assertRaises(abc.ResponseExit) as cm:
                self.run_awaitable(github.Host.process(request))
            self.assertEqual(cm.exception.response.status, 204)

    def test_process_opened(self):
        payload = {'action': github.PullRequestEvent.opened.value}
        request = FakeRequest(payload)
        result = self.run_awaitable(github.Host.process(request))
        self.assertEqual(result.event, github.PullRequestEvent.opened)

    def test_process_unlabeled(self):
        # Test a CLA label being removed.
        payload = {'action': github.PullRequestEvent.unlabeled.value,
                   'label': {'name': github.CLA_OK}}
        request = FakeRequest(payload)
        result = self.run_awaitable(github.Host.process(request))
        self.assertEqual(result.event, github.PullRequestEvent.unlabeled)
        # Test a non-CLA label being removed.
        payload['label']['name'] = 'missing something or other'
        request = FakeRequest(payload)
        with self.assertRaises(abc.ResponseExit) as cm:
            self.run_awaitable(github.Host.process(request))
        self.assertEqual(cm.exception.response.status, 204)

    def test_process_synchronize(self):
        payload = {'action': github.PullRequestEvent.synchronize.value}
        request = FakeRequest(payload)
        result = self.run_awaitable(github.Host.process(request))
        self.assertEqual(result.event, github.PullRequestEvent.synchronize)
