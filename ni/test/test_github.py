import copy
import json
import pathlib
import re
from urllib import parse

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
        assert expected == payload, f'{payload!r} != {expected!r}'

    async def delete(self, client, url):
        assert self._network[('DELETE', url)]


def example(file_name):
    this_dir = pathlib.Path(__file__).parent
    examples = this_dir/'examples'/'github'
    example = examples/file_name
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
        cls.opened_no_login_info_example = example('pr_opened_commit_has_no_login.json')
        cls.unlabeled_example = example('unlabeled.json')
        cls.synchronize_example = example('synchronize.json')
        cls.commits_example = example('commits.json')
        cls.empty_commits_example = example('empty_commits.json')
        cls.commits_url = 'https://api.github.com/repos/Microsoft/Pyjion/pulls/109/commits'
        cls.issues_example = example('issues.json')
        cls.issues_url = 'https://api.github.com/repos/Microsoft/Pyjion/issues/109'
        cls.labels_example = example('labels.json')
        cls.labels_url = 'https://api.github.com/repos/Microsoft/Pyjion/issues/109/labels'
        cls.comments_url = 'https://api.github.com/repos/Microsoft/Pyjion/issues/109/comments'

    def test_ping(self):
        # GitHub can ping a webhook to verify things are set up.
        # https://developer.github.com/webhooks/#ping-event
        payload = {'zen': 'something pithy'}
        request = util.FakeRequest(payload)
        request.headers['x-github-event'] = 'ping'
        with self.assertRaises(ni_abc.ResponseExit) as cm:
            self.run_awaitable(github.Host.process(util.FakeServerHost(),
                                                   request, util.FakeSession()))
        self.assertEqual(cm.exception.response.status, 200)

    def test_wrong_event(self):
        payload = {'zen': 'something pithy'}
        request = util.FakeRequest(payload)
        request.headers['x-github-event'] = 'issue'
        with self.assertRaises(TypeError):
            self.run_awaitable(github.Host.process(util.FakeServerHost(),
                                                   request, util.FakeSession()))

    def test_process_skipping(self):
        # Only create a ContribHost object if the PR is opened, unlabeled, or
        # synchronized.
        for event in github.PullRequestEvent:
            if event in self.acceptable:
                continue
            payload = {'action': event.value}
            request = util.FakeRequest(payload)
            with self.assertRaises(ni_abc.ResponseExit) as cm:
                self.run_awaitable(github.Host.process(util.FakeServerHost(),
                                                       request, util.FakeSession()))
            self.assertEqual(cm.exception.response.status, 204)

    def test_process_opened(self):
        request = util.FakeRequest(self.opened_example)
        result = self.run_awaitable(github.Host.process(util.FakeServerHost(),
                                                        request, util.FakeSession()))
        self.assertEqual(result.event, github.PullRequestEvent.opened)

    def test_process_unlabeled(self):
        # Test a CLA label being removed.
        unlabeled_example_CLA = copy.deepcopy(self.unlabeled_example)
        unlabeled_example_CLA['label']['name'] = github.CLA_OK
        request = util.FakeRequest(unlabeled_example_CLA)
        result = self.run_awaitable(github.Host.process(util.FakeServerHost(),
                                                        request, util.FakeSession()))
        self.assertEqual(result.event, github.PullRequestEvent.unlabeled)
        # Test a non-CLA label being removed.
        unlabeled_example_other = copy.deepcopy(self.unlabeled_example)
        unlabeled_example_other['label']['name'] = 'missing something or other'

        request = util.FakeRequest(unlabeled_example_other)
        request = util.FakeRequest(unlabeled_example_other)
        with self.assertRaises(ni_abc.ResponseExit) as cm:
            self.run_awaitable(github.Host.process(util.FakeServerHost(),
                                                   request, util.FakeSession()))
        self.assertEqual(cm.exception.response.status, 204)

    def test_process_synchronize(self):
        request = util.FakeRequest(self.synchronize_example)
        result = self.run_awaitable(github.Host.process(util.FakeServerHost(),
                                                        request, util.FakeSession()))
        self.assertEqual(result.event, github.PullRequestEvent.synchronize)

    def test_usernames(self):
        # Should grab logins from the creator of the PR, and both the author
        # and committer for every commit in the PR.
        responses = {("GET", self.commits_url): self.commits_example}
        session = util.FakeSession(responses=responses)
        contrib = github.Host(util.FakeServerHost(),
                              session,
                              github.PullRequestEvent.opened,
                              self.opened_example)
        got = self.run_awaitable(contrib.usernames())
        want = {'brettcannon', 'rbtcollins-author', 'rbtcollins-committer',
                'dstufft-author', 'dstufft-committer'}
        self.assertEqual(got, frozenset(want))

    def test_usernames_empty(self):
        # Handle the case where author and committer are both empty dicts.
        responses = {("GET", self.commits_url): self.empty_commits_example}
        session = util.FakeSession(responses=responses)
        contrib = github.Host(util.FakeServerHost(),
                              session,
                              github.PullRequestEvent.opened,
                              self.opened_no_login_info_example)
        got = self.run_awaitable(contrib.usernames())
        want = {'xpvpc'}
        self.assertEqual(got, frozenset(want))

    def test_labels_url(self):
        # Get the proper labels URL for a PR.
        responses = {("GET", self.issues_url): self.issues_example}
        session = util.FakeSession(responses=responses)
        contrib = github.Host(util.FakeServerHost(),
                              session,
                              github.PullRequestEvent.opened,
                              self.opened_example)
        got = self.run_awaitable(contrib.labels_url())
        want = self.labels_url.format_map({'/name': ''})
        self.assertEqual(got, want)

        got = self.run_awaitable(contrib.labels_url(github.CLA_OK))
        label = parse.quote(github.CLA_OK)
        want = f'{self.labels_url}/{label}'
        self.assertEqual(got, want)

    def test_current_label(self):

        responses = {("GET", self.issues_url): self.issues_example}
        # No label set.
        responses[("GET", self.labels_url)] = []
        session = util.FakeSession(responses)
        contrib = github.Host(util.FakeServerHost(),
                              session,
                              github.PullRequestEvent.synchronize,
                              self.synchronize_example)
        label = self.run_awaitable(contrib.current_label())
        self.assertIsNone(label)
        # One CLA label set.
        responses[("GET", self.labels_url)] = self.labels_example
        session = util.FakeSession(responses)
        contrib = github.Host(util.FakeServerHost(),
                              session,
                              github.PullRequestEvent.synchronize,
                              self.synchronize_example)
        label = self.run_awaitable(contrib.current_label())
        self.assertEqual(label, github.CLA_OK)
        # Two CLA labels set (error case).
        responses[("GET", self.labels_url)] = [{'name': github.CLA_OK}, {'name': github.NO_CLA}]
        session = util.FakeSession(responses)
        contrib = github.Host(util.FakeServerHost(),
                              session,
                              github.PullRequestEvent.synchronize,
                              self.synchronize_example)
        label = self.run_awaitable(contrib.current_label())
        # Just don't blow up.
        self.assertIsNotNone(label)

    def test_set_label(self):
        # If the status is "signed" then add the positive label, else use the
        # negative one.
        responses = {('GET', self.issues_url): self.issues_example,
                   ('POST', self.labels_url): [github.CLA_OK]}
        session = util.FakeSession(responses)
        contrib = github.Host(util.FakeServerHost(),
                              session,
                              github.PullRequestEvent.opened,
                              self.opened_example)
        label = self.run_awaitable(contrib.set_label({}))
        self.assertEqual(label, github.CLA_OK)


        responses[('POST', self.labels_url)] = [github.NO_CLA]
        session = util.FakeSession(responses)
        contrib = github.Host(util.FakeServerHost(),
                              session,
                              github.PullRequestEvent.opened,
                              self.opened_example)
        label = self.run_awaitable(contrib.set_label({ni_abc.Status.not_signed: {'username'}}))
        self.assertEqual(label, github.NO_CLA)
        self.run_awaitable(contrib.set_label({ni_abc.Status.username_not_found: {'username'}}))
        self.assertEqual(label, github.NO_CLA)

    def test_remove_label(self):
        # Remove all CLA-related labels.
        deletion_url = self.labels_url + '/' + parse.quote(github.CLA_OK)
        responses = {('GET', self.issues_url): self.issues_example,
                   ('GET', self.labels_url): self.labels_example,
                   ('DELETE', deletion_url): True}
        session = util.FakeSession(responses)
        contrib = github.Host(util.FakeServerHost(),
                              session,
                              github.PullRequestEvent.synchronize,
                              self.synchronize_example)
        deleted = self.run_awaitable(contrib.remove_label())
        self.assertEqual(deleted, github.CLA_OK)

        responses[('GET', self.labels_url)] = []
        session = util.FakeSession(responses)
        contrib = github.Host(util.FakeServerHost(),
                              session,
                              github.PullRequestEvent.synchronize,
                              self.synchronize_example)
        deleted = self.run_awaitable(contrib.remove_label())
        self.assertIsNone(deleted)

    def test_comment(self):
        # Add a comment related to the status.
        contrib = github.Host(util.FakeServerHost(),
                              util.FakeSession(),
                              github.PullRequestEvent.opened,
                              self.opened_example)
        message = self.run_awaitable(contrib.comment({}))
        self.assertIsNone(message)

        expected = {'body':
                    github.NO_CLA_TEMPLATE.format(
                        not_signed=github.NO_CLA_BODY.format('@username'),
                        username_not_found='',
                    )}
        responses = {('POST', self.comments_url): expected}
        session = util.FakeSession(responses)
        contrib = github.Host(util.FakeServerHost(),
                              session,
                              github.PullRequestEvent.opened,
                              self.opened_example)
        message = self.run_awaitable(contrib.comment({ni_abc.Status.not_signed: {'username'}}))
        self.assertEqual(message, expected['body'])

        expected['body'] = github.NO_CLA_TEMPLATE.format(
            not_signed='',
            username_not_found=github.NO_USERNAME_BODY.format('@username'),
        )
        responses[('POST', self.comments_url)] = expected
        session = util.FakeSession(responses)
        contrib = github.Host(util.FakeServerHost(),
                              session,
                              github.PullRequestEvent.opened,
                              self.opened_example)
        message = self.run_awaitable(contrib.comment({ni_abc.Status.username_not_found: {'username'}}))
        self.assertEqual(expected['body'], message)

        # Test for when multiple users didn't sign the CLA and are not found
        responses[('POST', self.comments_url)] = expected
        session = util.FakeSession(responses)
        contrib = github.Host(util.FakeServerHost(),
                              session,
                              github.PullRequestEvent.opened,
                              self.opened_example)
        message = self.run_awaitable(
            contrib.comment({
                ni_abc.Status.not_signed: {'ns_a', 'ns_b'},
                ni_abc.Status.username_not_found: {'unf_a', 'unf_b'},
            })
        )
        self.assertTrue('@ns_a, @ns_b' in message or '@ns_b, @ns_a' in message)
        self.assertTrue('@unf_a, @unf_b' in message or '@unf_b, @unf_a' in message)
        regex_placeholder = 'USERS_REGEX'
        escaped_no_cla = re.escape(github.NO_CLA_BODY.format(regex_placeholder))
        self.assertRegex(
            message,
            re.compile(escaped_no_cla.replace(regex_placeholder, '@ns_(a|b), @ns_(a|b)'))
        )
        escaped_no_username = re.escape(github.NO_USERNAME_BODY.format(regex_placeholder))
        self.assertRegex(
            message,
            re.compile(escaped_no_username.replace(regex_placeholder, '@unf_(a|b), @unf_(a|b)'))
        )

    def test_update_opened(self):
        # Adding CLA status on an opened PR.
        comment = github.NO_CLA_TEMPLATE.format(
            not_signed=github.NO_CLA_BODY.format('@username'),
            username_not_found='',
        )
        responses = {('GET', self.issues_url): self.issues_example,
                   ('POST', self.labels_url): [github.NO_CLA],
                   ('POST', self.comments_url): {'body': comment}}
        contrib = github.Host(util.FakeServerHost(),
                              util.FakeSession(responses),
                              github.PullRequestEvent.opened,
                              self.opened_example)
        self.noException(contrib.update({ni_abc.Status.not_signed: {'username'}}))

    def test_update_unlabeled(self):
        # Adding CLA status to a PR that just lost its CLA label.
        responses = {('GET', self.issues_url): self.issues_example,
                   ('POST', self.labels_url): [github.CLA_OK]}
        contrib = github.Host(util.FakeServerHost(),
                              util.FakeSession(responses),
                              github.PullRequestEvent.unlabeled,
                              self.unlabeled_example)
        self.noException(contrib.update({}))

    def test_update_synchronize(self):
        # Update the PR after it's synchronized.
        responses = {('GET', self.issues_url): self.issues_example}
        # CLA signed and already labeled as such.
        responses[('GET', self.labels_url)] = self.labels_example
        session = util.FakeSession(responses)
        contrib = github.Host(util.FakeServerHost(),
                              session,
                              github.PullRequestEvent.synchronize,
                              self.synchronize_example)
        self.noException(contrib.update({}))
        # CLA signed, but not labeled as such.
        responses[('GET', self.labels_url)] = [{'name': github.NO_CLA}]
        session = util.FakeSession(responses)
        contrib = github.Host(util.FakeServerHost(),
                              session,
                              github.PullRequestEvent.synchronize,
                              self.synchronize_example)
        deletion_url = self.run_awaitable(
                contrib.labels_url(github.NO_CLA))
        responses[('DELETE', deletion_url)] = [github.NO_CLA]
        session = util.FakeSession(responses)
        contrib = github.Host(util.FakeServerHost(),
                              session,
                              github.PullRequestEvent.synchronize,
                              self.synchronize_example)
        self.noException(contrib.update({}))
        # CLA not signed and already labeled as such.
        responses[('GET', self.labels_url)] = [{'name': github.NO_CLA}]
        session = util.FakeSession(responses)
        contrib = github.Host(util.FakeServerHost(),
                              session,
                              github.PullRequestEvent.synchronize,
                              self.synchronize_example)
        self.noException(contrib.update({ni_abc.Status.not_signed: {'username'}}))
        # CLA not signed, but currently labeled as such.
        responses[('GET', self.labels_url)] = [{'name': github.CLA_OK}]
        session = util.FakeSession(responses)
        contrib = github.Host(util.FakeServerHost(),
                              session,
                              github.PullRequestEvent.synchronize,
                              self.synchronize_example)
        deletion_url = self.run_awaitable(
                contrib.labels_url(github.CLA_OK))
        responses[('DELETE', deletion_url)] = [github.CLA_OK]
        comment = github.NO_CLA_TEMPLATE.format(
            not_signed=github.NO_CLA_BODY.format('@username'),
            username_not_found='',
        )
        responses[('POST', self.comments_url)] = {'body': comment}
        session = util.FakeSession(responses)
        contrib = github.Host(util.FakeServerHost(),
                              session,
                              github.PullRequestEvent.synchronize,
                              self.synchronize_example)
        self.noException(contrib.update({ni_abc.Status.not_signed: {'username'}}))
        # No GitHub username, but already labeled as no CLA.
        responses[('GET', self.labels_url)] = [{'name': github.NO_CLA}]
        session = util.FakeSession(responses)
        contrib = github.Host(util.FakeServerHost(),
                              session,
                              github.PullRequestEvent.synchronize,
                              self.synchronize_example)
        self.noException(contrib.update({ni_abc.Status.username_not_found: {'username'}}))
        # No GitHub username, but labeled as signed.
        responses[('GET', self.labels_url)] = [{'name': github.CLA_OK}]
        session = util.FakeSession(responses)
        contrib = github.Host(util.FakeServerHost(),
                              session,
                              github.PullRequestEvent.synchronize,
                              self.synchronize_example)
        deletion_url = self.run_awaitable(
                contrib.labels_url(github.CLA_OK))
        responses[('DELETE', deletion_url)] = [github.CLA_OK]
        comment = github.NO_CLA_TEMPLATE.format(
            not_signed='',
            username_not_found=github.NO_USERNAME_BODY.format('@username'),
        )
        responses[('POST', self.comments_url)] = {'body': comment}
        session = util.FakeSession(responses)
        contrib = github.Host(util.FakeServerHost(),
                              session,
                              github.PullRequestEvent.synchronize,
                              self.synchronize_example)
        self.noException(contrib.update({ni_abc.Status.username_not_found: {'username'}}))
