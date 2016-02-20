import os
import sys
import traceback

from . import abc


class Host(abc.ServerHost):

    """Server hosting on Heroku."""

    @staticmethod
    def port():
        return int(os.environ['PORT'])

    @staticmethod
    def log(exc: Exception):
        """Log an exception and its traceback to stderr."""
        traceback.print_exception(type(exc), exc, exc.__traceback__,
                                  file=sys.stderr)
