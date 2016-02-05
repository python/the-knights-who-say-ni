import asyncio
import unittest

from aiohttp import web

from .. import github


class GitHubTests(unittest.TestCase):

    acceptable = {github.PullRequestEvent.opened,
                  github.PullRequestEvent.unlabeled,
                  github.PullRequestEvent.synchronize}

    def test_process_skipping(self):
        # Only create a ContibHost object if the PR is opened, unlabeled, or
        # synchronized.
        for event in github.PullRequestEvent:
            if event in self.acceptable:
                continue
            request = {'action': event.value}
            loop = asyncio.get_event_loop()
            self.addCleanup(loop.close)
            result = loop.run_until_complete(github.Host.process(request))
            self.assertIsNone(result)