import os
import sys
import traceback

from . import abc


class Host(abc.ServerHost):

    """Server hosting on Heroku."""

    def port(self):
        return int(os.environ['PORT'])

    def log(self, exc: Exception):
        """Log an exception and its traceback to stderr."""
        traceback.print_exception(type(exc), exc, exc.__traceback__,
                                  file=sys.stderr)
