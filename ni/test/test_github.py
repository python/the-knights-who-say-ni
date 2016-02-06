import asyncio
import unittest

from aiohttp import web

from .. import github


class GitHubTests(unittest.TestCase):

    acceptable = {github.PullRequestEvent.opened,
                  github.PullRequestEvent.unlabeled,
                  github.PullRequestEvent.synchronize}

    def test_ping(self):
        # GitHub can ping a webhook to verify things are set up.
        # https://developer.github.com/webhooks/#ping-event
        request = {'zen': 'something pithy'}
        loop = asyncio.new_event_loop()
        self.addCleanup(loop.close)
        result = loop.run_until_complete(github.Host.process(request))
        self.assertIsNone(result)

    def test_process_skipping(self):
        # Only create a ContibHost object if the PR is opened, unlabeled, or
        # synchronized.
        loop = asyncio.new_event_loop()
        self.addCleanup(loop.close)
        for event in github.PullRequestEvent:
            if event in self.acceptable:
                continue
            request = {'action': event.value}
            result = loop.run_until_complete(github.Host.process(request))
            self.assertIsNone(result)

    def test_nothing_to_do(self):
        # Return a 204.
        response = github.Host.nothing_to_do()
        self.assertEqual(response.status, 204)
