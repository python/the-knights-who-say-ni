import asyncio
import copy
from http import client
import json
import pathlib
import unittest
from urllib import parse

from aiohttp import hdrs, web

from .. import abc as ni_abc
from .. import github
from . import util


class OfflineHost(github.Host):

    """A subclass of github.Host which does not touch the network."""

    def __init__(self, *args, network, **kwargs):
        super().__init__(*args, **kwargs)
        self._network = network

    async def get(self, client, url):
        return self._network[('GET', url)]

    async def post(self, client, url, payload):
        expected = self._network[('POST', url)]
        assert expected == payload, '{!r} != {!r}'.format(payload, expected)

    async def delete(self, client, url):
        assert self._network[('DELETE', url)]


def example(file_name):
    this_dir = pathlib.Path(__file__).parent
    examples = this_dir / 'examples' / 'github'
    example = examples / file_name
    with example.open('r', encoding='utf-8') as file:
        return json.load(file)


class GitHubTests(util.TestCase):

    acceptable = {github.PullRequestEvent.opened,
                  github.PullRequestEvent.unlabeled,
                  github.PullRequestEvent.synchronize}

    @classmethod
    def setUpClass(cls):
        github.EASTEREGG_PROBABILITY = 0.0
        cls.opened_example = example('opened.json')
        cls.unlabeled_example = example('unlabeled.json')
        cls.synchronize_example = example('synchronize.json')
        cls.commits_example = example('commits.json')
        cls.commits_url = 'https://api.github.com/repos/Microsoft/Pyjion/pulls/109/commits'
        cls.issues_example = example('issues.json')
        cls.issues_url = 'https://api.github.com/repos/Microsoft/Pyjion/issues/109'
        cls.labels_example = example('labels.json')
        cls.labels_url = 'https://api.github.com/repos/Microsoft/Pyjion/issues/109/labels'
        cls.comments_url = 'https://api.github.com/repos/Microsoft/Pyjion/issues/109/comments'

    def test_bad_content_type(self):
        # Only accept 'application/json'.
        # https://developer.github.com/webhooks/creating/#content-type
        request = util.FakeRequest(content_type='application/x-www-form-urlencoded')
        with self.assertRaises(ni_abc.ResponseExit) as cm:
            self.run_awaitable(github.Host.process(util.FakeServerHost(), request))
        self.assertEqual(cm.exception.response.status, 415)

    def test_ping(self):
        # GitHub can ping a webhook to verify things are set up.
        # https://developer.github.com/webhooks/#ping-event
        payload = {'zen': 'something pithy'}
        with self.assertRaises(ni_abc.ResponseExit) as cm:
            self.run_awaitable(github.Host.process(util.FakeServerHost(),
                                                   util.FakeRequest(payload)))
        self.assertEqual(cm.exception.response.status, 200)

    def test_process_skipping(self):
        # Only create a ContibHost object if the PR is opened, unlabeled, or
        # synchronized.
        for event in github.PullRequestEvent:
            if event in self.acceptable:
                continue
            payload = {'action': event.value}
            request = util.FakeRequest(payload)
            with self.assertRaises(ni_abc.ResponseExit) as cm:
                self.run_awaitable(github.Host.process(util.FakeServerHost(),
                                                       request))
            self.assertEqual(cm.exception.response.status, 204)

    def test_process_opened(self):
        request = util.FakeRequest(self.opened_example)
        result = self.run_awaitable(github.Host.process(util.FakeServerHost(),
                                                        request))
        self.assertEqual(result.event, github.PullRequestEvent.opened)

    def test_process_unlabeled(self):
        # Test a CLA label being removed.
        unlabeled_example_CLA = copy.deepcopy(self.unlabeled_example)
        unlabeled_example_CLA['label']['name'] = github.CLA_OK
        request = util.FakeRequest(unlabeled_example_CLA)
        result = self.run_awaitable(github.Host.process(util.FakeServerHost(),
                                                        request))
        self.assertEqual(result.event, github.PullRequestEvent.unlabeled)
        # Test a non-CLA label being removed.
        unlabeled_example_other = copy.deepcopy(self.unlabeled_example)
        unlabeled_example_other['label']['name'] = 'missing something or other'
        request = util.FakeRequest(unlabeled_example_other)
        with self.assertRaises(ni_abc.ResponseExit) as cm:
            self.run_awaitable(github.Host.process(util.FakeServerHost(),
                                                   request))
        self.assertEqual(cm.exception.response.status, 204)

    def test_process_synchronize(self):
        request = util.FakeRequest(self.synchronize_example)
        result = self.run_awaitable(github.Host.process(util.FakeServerHost(),
                                                        request))
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
        contrib = OfflineHost(util.FakeServerHost(),
                              github.PullRequestEvent.opened,
                              self.opened_example,
                              network=network)
        got = self.run_awaitable(contrib.usernames(util.FakeSession()))
        want = {'brettcannon', 'rbtcollins-author', 'rbtcollins-committer',
                'dstufft-author', 'dstufft-committer'}
        self.assertEqual(got, frozenset(want))

    def test_labels_url(self):
        # Get the proper labels URL for a PR.
        network = {('GET', self.issues_url): self.issues_example}
        contrib = OfflineHost(util.FakeServerHost(),
                              github.PullRequestEvent.opened,
                              self.opened_example,
                              network=network)
        got = self.run_awaitable(contrib.labels_url(util.FakeSession()))
        want = self.labels_url.format_map({'/name': ''})
        self.assertEqual(got, want)

        got = self.run_awaitable(contrib.labels_url(util.FakeSession(),
                                                    github.CLA_OK))
        label = parse.quote(github.CLA_OK)
        want = '{}/{}'.format(self.labels_url, label)
        self.assertEqual(got, want)

    def test_current_label(self):
        # Test getting the current CLA label (if any).
        network = {('GET', self.issues_url): self.issues_example}
        contrib = OfflineHost(util.FakeServerHost(),
                              github.PullRequestEvent.synchronize,
                              self.synchronize_example,
                              network=network)
        # No label set.
        network[('GET', self.labels_url)] = []
        label = self.run_awaitable(contrib.current_label(util.FakeSession()))
        self.assertIsNone(label)
        # One CLA label set.
        network[('GET', self.labels_url)] = self.labels_example
        label = self.run_awaitable(contrib.current_label(util.FakeSession()))
        self.assertEqual(label, github.CLA_OK)
        # Two CLA labels set (error case).
        network[('GET', self.labels_url)] = [{'name': github.CLA_OK},
                                             {'name': github.NO_CLA}]
        label = self.run_awaitable(contrib.current_label(util.FakeSession()))
        # Just don't blow up.
        self.assertIsNotNone(label)

    def test_set_label(self):
        # If the status is "signed" then add the positive label, else use the
        # negative one.
        network = {('GET', self.issues_url): self.issues_example,
                   ('POST', self.labels_url): [github.CLA_OK]}
        contrib = OfflineHost(util.FakeServerHost(),
                              github.PullRequestEvent.opened,
                              self.opened_example,
                              network=network)
        label = self.run_awaitable(contrib.set_label(util.FakeSession(),
                                                     ni_abc.Status.signed))
        self.assertEqual(label, github.CLA_OK)
        network[('POST', self.labels_url)] = [github.NO_CLA]
        label = self.run_awaitable(contrib.set_label(util.FakeSession(),
                                                     ni_abc.Status.not_signed))
        self.assertEqual(label, github.NO_CLA)
        self.run_awaitable(contrib.set_label(util.FakeSession(),
                                             ni_abc.Status.username_not_found))
        self.assertEqual(label, github.NO_CLA)

    def test_remove_label(self):
        # Remove all CLA-related labels.
        deletion_url = self.labels_url + '/' + parse.quote(github.CLA_OK)
        network = {('GET', self.issues_url): self.issues_example,
                   ('GET', self.labels_url): self.labels_example,
                   ('DELETE', deletion_url): True}
        contrib = OfflineHost(util.FakeServerHost(),
                              github.PullRequestEvent.synchronize,
                              self.synchronize_example,
                              network=network)
        deleted = self.run_awaitable(contrib.remove_label(util.FakeSession()))
        self.assertEqual(deleted, github.CLA_OK)
        network[('GET', self.labels_url)] = []
        deleted = self.run_awaitable(contrib.remove_label(util.FakeSession()))
        self.assertIsNone(deleted)

    def test_comment(self):
        # Add a comment related to the status.
        network = {}
        contrib = OfflineHost(util.FakeServerHost(),
                              github.PullRequestEvent.opened,
                              self.opened_example,
                              network=network)
        message = self.run_awaitable(contrib.comment(util.FakeSession(),
                                                     ni_abc.Status.signed))
        self.assertIsNone(message)
        expected = {'body':
                    github.NO_CLA_TEMPLATE.format(body=github.NO_CLA_BODY)}
        network[('POST', self.comments_url)] = expected
        message = self.run_awaitable(contrib.comment(util.FakeSession(),
                                                     ni_abc.Status.not_signed))
        self.assertEqual(message, expected['body'])
        expected['body'] = github.NO_CLA_TEMPLATE.format(
                body=github.NO_USERNAME_BODY)
        network[('POST', self.comments_url)] = expected
        message = self.run_awaitable(contrib.comment(util.FakeSession(),
                                                     ni_abc.Status.username_not_found))
        self.assertEqual(expected['body'], message)

    def test_update_opened(self):
        # Adding CLA status on an opened PR.
        comment = github.NO_CLA_TEMPLATE.format(body=github.NO_CLA_BODY)
        network = {('GET', self.issues_url): self.issues_example,
                   ('POST', self.labels_url): [github.NO_CLA],
                   ('POST', self.comments_url): {'body': comment}}
        contrib = OfflineHost(util.FakeServerHost(),
                              github.PullRequestEvent.opened,
                              self.opened_example,
                              network=network)
        self.noException(contrib.update(util.FakeSession(), ni_abc.Status.not_signed))

    def test_update_unlabeled(self):
        # Adding CLA status to a PR that just lost its CLA label.
        network = {('GET', self.issues_url): self.issues_example,
                   ('POST', self.labels_url): [github.CLA_OK]}
        contrib = OfflineHost(util.FakeServerHost(),
                              github.PullRequestEvent.unlabeled,
                              self.unlabeled_example,
                              network=network)
        self.noException(contrib.update(util.FakeSession(), ni_abc.Status.signed))

    def test_update_synchronize(self):
        # Update the PR after it's synchronized.
        network = {('GET', self.issues_url): self.issues_example}
        contrib = OfflineHost(util.FakeServerHost(),
                              github.PullRequestEvent.synchronize,
                              self.synchronize_example,
                              network=network)
        # CLA signed and already labeled as such.
        network[('GET', self.labels_url)] = self.labels_example
        self.noException(contrib.update(util.FakeSession(), ni_abc.Status.signed))
        # CLA signed, but not labeled as such.
        network[('GET', self.labels_url)] = [{'name': github.NO_CLA}]
        deletion_url = self.run_awaitable(
                contrib.labels_url(util.FakeSession(), github.NO_CLA))
        network[('DELETE', deletion_url)] = [github.NO_CLA]
        self.noException(contrib.update(util.FakeSession(), ni_abc.Status.signed))
        # CLA not signed and already labeled as such.
        network[('GET', self.labels_url)] = [{'name': github.NO_CLA}]
        self.noException(contrib.update(util.FakeSession(), ni_abc.Status.not_signed))
        # CLA not signed, but currently labeled as such.
        network[('GET', self.labels_url)] = [{'name': github.CLA_OK}]
        deletion_url = self.run_awaitable(
                contrib.labels_url(util.FakeSession(),github.CLA_OK))
        network[('DELETE', deletion_url)] = [github.CLA_OK]
        comment = github.NO_CLA_TEMPLATE.format(body=github.NO_CLA_BODY)
        network[('POST', self.comments_url)] = {'body': comment}
        self.noException(contrib.update(util.FakeSession(),
                                        ni_abc.Status.not_signed))
        # No GitHub username, but already labeled as no CLA.
        network[('GET', self.labels_url)] = [{'name': github.NO_CLA}]
        self.noException(contrib.update(util.FakeSession(),
                                        ni_abc.Status.username_not_found))
        # No GitHub username, but labeled as signed.
        network[('GET', self.labels_url)] = [{'name': github.CLA_OK}]
        deletion_url = self.run_awaitable(
                contrib.labels_url(util.FakeSession(), github.CLA_OK))
        network[('DELETE', deletion_url)] = [github.CLA_OK]
        comment = github.NO_CLA_TEMPLATE.format(body=github.NO_USERNAME_BODY)
        network[('POST', self.comments_url)] = {'body': comment}
        self.noException(contrib.update(util.FakeSession(),
                                        ni_abc.Status.username_not_found))


class NetworkingTests(util.TestCase):

    def test_get(self):
        # Test a GET request to a live GitHub API URL.
        contrib = github.Host(util.FakeServerHost(),
                              github.PullRequestEvent.opened, {})
        url = 'https://api.github.com/repos/Microsoft/Pyjion/issues/109'
        payload = {'hello': 'world'}
        fake_session = util.FakeSession(data=payload)
        returned = self.noException(contrib.get(fake_session, url))
        self.assertEqual(payload, returned)
        self.assertEqual(fake_session.url, url)
        self.assertIn('Authorization', fake_session.headers)
        self.assertEqual(fake_session.headers['Authorization'],
                          'token ' + util.FakeServerHost.auth_token)
        # Test making a failed request.
        failed_response = util.FakeResponse(status=404)
        fake_session = util.FakeSession(response=failed_response)
        with self.assertRaises(client.HTTPException):
            self.run_awaitable(contrib.get(fake_session, url))

    def test_post(self):
        contrib = github.Host(util.FakeServerHost(), None, None)
        data = {'hello': 'world'}
        url = 'https://api.github.com/repos/Microsoft/Pyjion/issues/109'
        fake_session = util.FakeSession()
        self.noException(contrib.post(fake_session, url, data))
        self.assertEqual(fake_session.url, url)
        json_string = fake_session.data.decode('utf-8')
        self.assertEqual(json.loads(json_string), data)
        user_agent = fake_session.headers[hdrs.USER_AGENT]
        self.assertEqual(user_agent, util.FakeServerHost.user_agent_name)
        content_type = fake_session.headers[hdrs.CONTENT_TYPE]
        self.assertTrue(content_type.startswith('application/json'))
        self.assertIn('Authorization', fake_session.headers)
        self.assertEqual(fake_session.headers['Authorization'],
                          'token ' + util.FakeServerHost.auth_token)
        # Test making a failed request.
        failed_response = util.FakeResponse(status=404)
        fake_session = util.FakeSession(response=failed_response)
        with self.assertRaises(client.HTTPException):
            self.run_awaitable(contrib.post(fake_session, url, data))
        # Test no user-agent.
        fake_server = util.FakeServerHost()
        fake_server.user_agent_name = None
        contrib = github.Host(fake_server, None, None)
        data = {'hello': 'world'}
        url = 'https://api.github.com/repos/Microsoft/Pyjion/issues/109'
        fake_session = util.FakeSession()
        self.noException(contrib.post(fake_session, url, data))
        self.assertEqual(fake_session.url, url)
        json_string = fake_session.data.decode('utf-8')
        self.assertEqual(json.loads(json_string), data)
        self.assertNotIn(hdrs.USER_AGENT, fake_session.headers)

    def test_delete(self):
        contrib = github.Host(util.FakeServerHost(), None, None)
        data = {'hello': 'world'}
        url = 'https://api.github.com/repos/Microsoft/Pyjion/issues/109'
        fake_session = util.FakeSession()
        self.noException(contrib.delete(fake_session, url))
        self.assertEqual(fake_session.url, url)
        self.assertIn('Authorization', fake_session.headers)
        self.assertEqual(fake_session.headers['Authorization'],
                          'token ' + util.FakeServerHost.auth_token)
        # Test making a failed request.
        failed_response = util.FakeResponse(status=404)
        fake_session = util.FakeSession(response=failed_response)
        with self.assertRaises(client.HTTPException):
            self.run_awaitable(contrib.delete(fake_session, url))
