import contextlib
import io
import os
import random
import unittest

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

    def test_contrib_secret_token(self):
        secret_token = 'some_secret_token'
        os.environ['GH_SECRET_TOKEN'] = secret_token
        self.assertEqual(self.server.contrib_secret_token(), secret_token)

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
