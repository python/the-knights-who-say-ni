import asyncio
import copy
import json
import pathlib
import unittest
from urllib import parse

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


class OfflineHost(github.Host):

    """A subclass of github.Host which does not touch the network."""

    def __init__(self, *args, network, **kwargs):
        super().__init__(*args, **kwargs)
        self._network = network

    async def get(self, url):
        return self._network[('GET', url)]

    async def post(self, url, payload):
        assert self._network[('POST', url)] == payload


class GitHubTests(unittest.TestCase):

    acceptable = {github.PullRequestEvent.opened,
                  github.PullRequestEvent.unlabeled,
                  github.PullRequestEvent.synchronize}

    @classmethod
    def setUpClass(cls):
        this_dir = pathlib.Path(__file__).parent
        examples = this_dir / 'examples' / 'github'
        opened_example = examples / 'opened.json'
        with opened_example.open('r') as file:
            cls.opened_example = json.load(file)

        unlabeled_example = examples / 'unlabeled.json'
        with unlabeled_example.open('r') as file:
            cls.unlabeled_example = json.load(file)

        sync_example = examples / 'synchronize.json'
        with sync_example.open('r') as file:
            cls.synchronize_example = json.load(file)

        commits_example = examples / 'commits.json'
        with commits_example.open('r') as file:
            cls.commits_example = json.load(file)
        cls.commits_url = 'https://api.github.com/repos/Microsoft/Pyjion/pulls/109/commits'

        issues_example = examples / 'issues.json'
        with issues_example.open('r') as file:
            cls.issues_example = json.load(file)
        cls.issues_url = 'https://api.github.com/repos/Microsoft/Pyjion/issues/109'

        labels_example = examples / 'labels.json'
        with labels_example.open('r') as file:
            cls.labels_example = json.load(file)
        cls.labels_url = 'https://api.github.com/repos/Microsoft/Pyjion/issues/109/labels'

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
        request = FakeRequest(self.opened_example)
        result = self.run_awaitable(github.Host.process(request))
        self.assertEqual(result.event, github.PullRequestEvent.opened)

    def test_process_unlabeled(self):
        # Test a CLA label being removed.
        unlabeled_example_CLA = copy.deepcopy(self.unlabeled_example)
        unlabeled_example_CLA['label']['name'] = github.CLA_OK
        request = FakeRequest(unlabeled_example_CLA)
        result = self.run_awaitable(github.Host.process(request))
        self.assertEqual(result.event, github.PullRequestEvent.unlabeled)
        # Test a non-CLA label being removed.
        unlabeled_example_other = copy.deepcopy(self.unlabeled_example)
        unlabeled_example_other['label']['name'] = 'missing something or other'
        request = FakeRequest(unlabeled_example_other)
        with self.assertRaises(abc.ResponseExit) as cm:
            self.run_awaitable(github.Host.process(request))
        self.assertEqual(cm.exception.response.status, 204)

    def test_process_synchronize(self):
        request = FakeRequest(self.synchronize_example)
        result = self.run_awaitable(github.Host.process(request))
        self.assertEqual(result.event, github.PullRequestEvent.synchronize)

    def test_check_response(self):
        # Throw a fit for anything that isn't a 2XX response.
        github.Host.check_response(web.Response(status=202))
        with self.assertRaises(Exception):
            github.Host.check_response(web.Response(status=301))
        with self.assertRaises(Exception):
            github.Host.check_response(web.Response(status=404))
        with self.assertRaises(Exception):
            github.Host.check_response(web.Response(status=502))

    def test_usernames(self):
        # Should grab logins from the PR creator of the PR, and both the author
        # and committer for every commit in the PR.
        what = ('GET', self.commits_url)
        network = {what: self.commits_example}
        contrib = OfflineHost(github.PullRequestEvent.opened,
                              self.opened_example, network=network)
        got = self.run_awaitable(contrib.usernames())
        want = {'brettcannon', 'rbtcollins-author', 'rbtcollins-committer',
                'dstufft-author', 'dstufft-committer'}
        self.assertEqual(got, frozenset(want))

    def test_labels_url(self):
        # Get the proper labels URL for a PR.
        network = {('GET', self.issues_url): self.issues_example}
        contrib = OfflineHost(github.PullRequestEvent.opened,
                              self.opened_example, network=network)
        got = self.run_awaitable(contrib.labels_url())
        want = self.labels_url.format_map({'/name': ''})
        self.assertEqual(got, want)

        got = self.run_awaitable(contrib.labels_url(github.CLA_OK))
        label = parse.quote(github.CLA_OK)
        want = '{}/{}'.format(self.labels_url, label)
        self.assertEqual(got, want)

    def test_set_label(self):
        # If the status is "signed" then add the positive label, else use the
        # negative one.
        network = {('GET', self.issues_url): self.issues_example,
                   ('POST', self.labels_url): [github.CLA_OK]}
        contrib = OfflineHost(github.PullRequestEvent.opened,
                              self.opened_example, network=network)
        label = self.run_awaitable(contrib.set_label(abc.Status.signed))
        self.assertEqual(label, github.CLA_OK)
        network[('POST', self.labels_url)] = [github.NO_CLA]
        label = self.run_awaitable(contrib.set_label(abc.Status.not_signed))
        self.assertEqual(label, github.NO_CLA)
        self.run_awaitable(contrib.set_label(abc.Status.username_not_found))
        self.assertEqual(label, github.NO_CLA)

    def test_remove_labels(self):
        # Remove all CLA-related labels.
        # XXX
        pass

    def test_comment(self):
        # Add a comment related to the status.
        # XXX
        pass

    def test_update(self):
        # Update a PR based on the CLA status.
        # Opened.
        # XXX
        # Unlabled.
        network = {('GET', self.issues_url): self.issues_example}
        contrib = OfflineHost(github.PullRequestEvent.unlabeled,
                              self.unlabeled_example, network=network)
        labels_url = self.run_awaitable(contrib.labels_url())
        network[('POST', labels_url)] = [github.CLA_OK]
        # Should not raise an exception.
        self.run_awaitable(contrib.update(abc.Status.signed))
        # Synchronized.
        # XXX
