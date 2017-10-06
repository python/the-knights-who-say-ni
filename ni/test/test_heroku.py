import contextlib
import io
import os
import random
import unittest
import unittest.mock as mock

from .. import heroku


class HerokuTests(unittest.TestCase):

    def setUp(self):
        self.server = heroku.Host()

    def test_port(self):
        # The port number comes from the PORT environment variable.
        old_port = os.environ.get('PORT')
        def reset_port():
            if old_port is None:
                del os.environ['PORT']
            else:
                os.environ['PORT'] = old_port
        port = random.randint(1, 2**16 - 1)
        os.environ['PORT'] = str(port)
        self.addCleanup(reset_port)
        self.assertEqual(self.server.port(), port)

    def test_contrib_auth_token(self):
        auth_token = 'some_oauth_token'
        os.environ['GH_AUTH_TOKEN'] = auth_token
        self.assertEqual(self.server.contrib_auth_token(), auth_token)

    def test_contrib_secret(self):
        secret = "secret"
        os.environ["GH_SECRET"] = secret
        self.assertEqual(self.server.contrib_secret(), secret)

    def test_user_agent(self):
        user_agent = 'Testing-Agent'
        self.assertIsNone(self.server.user_agent())
        os.environ['USER_AGENT'] = user_agent
        self.assertEqual(self.server.user_agent(), user_agent)

    def test_log_exception(self):
        # Traceback and exception should be written to stderr.
        exc_type = NotImplementedError
        exc_message = 'hello'
        try:
            raise exc_type(exc_message)
        except Exception as caught:
            exc = caught
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.server.log_exception(exc)
        logged = stderr.getvalue()
        self.assertIn(exc_type.__name__, logged)
        self.assertIn(exc_message, logged)
        self.assertIn('Traceback', logged)

    def test_log(self):
        message = "something happened"
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.server.log(message)
        self.assertEqual(stderr.getvalue(), message + "\n")

    def test_trusted_users(self):
        trusted_users = "miss-islington,bedevere-bot,the-knights-who-say-ni"
        os.environ["CLA_TRUSTED_USERS"] = trusted_users
        self.assertEqual(self.server.trusted_users(),
                         frozenset(["miss-islington",
                                    "bedevere-bot",
                                    "the-knights-who-say-ni"])
                         )

    def test_no_trusted_users(self):
        usernames = frozenset(['miss-islington', 'bedevere-bot'])
        self.assertEqual(self.server.usernames_to_check(usernames), usernames)

    @mock.patch.dict(os.environ, {'CLA_TRUSTED_USERS': 'bedevere-bot'})
    def test_not_comma_separated_ignore_list(self):
        usernames = frozenset(['miss-islington', 'bedevere-bot'])
        self.assertEqual(self.server.usernames_to_check(usernames),
                         frozenset(['miss-islington']))

    @mock.patch.dict(os.environ, {'CLA_TRUSTED_USERS': 'bedevere-bot,miss-islington'})
    def test_comma_separated_ignore_list(self):
        usernames = frozenset(['brettcannon', 'bedevere-bot', 'miss-islington'])
        self.assertEqual(self.server.usernames_to_check(usernames),
                         frozenset(['brettcannon']))

    @mock.patch.dict(os.environ, {'CLA_TRUSTED_USERS': 'bedevere-bot, miss-islington'})
    def test_comma_separated_ignore_list_with_spaces(self):
        usernames = frozenset(['brettcannon', 'bedevere-bot', 'miss-islington'])
        self.assertEqual(self.server.usernames_to_check(usernames),
                         frozenset(['brettcannon']))

    @mock.patch.dict(os.environ, {'CLA_TRUSTED_USERS': 'bedevere-bot, Miss-Islington'})
    def test_ignore_list_ignore_case(self):
        usernames = frozenset(['brettcannon', 'bedevere-bot', 'miss-islington'])
        self.assertEqual(self.server.usernames_to_check(usernames),
                         frozenset(['brettcannon']))
