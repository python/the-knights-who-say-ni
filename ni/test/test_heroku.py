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