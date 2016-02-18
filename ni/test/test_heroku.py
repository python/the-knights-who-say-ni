import contextlib
import io
import os
import random
import unittest

from .. import heroku


class HerokuTests(unittest.TestCase):

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
        server = heroku.Host()
        self.assertEqual(server.port(), port)

    def test_log(self):
        # Traceback and exception should be written to stderr.
        server = heroku.Host()
        exc_type = NotImplementedError
        exc_message = 'hello'
        try:
            raise exc_type(exc_message)
        except Exception as caught:
            exc = caught
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            server.log(exc)
        logged = stderr.getvalue()
        self.assertIn(exc_type.__name__, logged)
        self.assertIn(exc_message, logged)
        self.assertIn('Traceback', logged)
