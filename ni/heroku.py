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
    def contrib_auth_token():
        return os.environ['GH_AUTH_TOKEN']

    @staticmethod
    def log_exception(exc):
        """Log an exception and its traceback to stderr."""
        traceback.print_exception(type(exc), exc, exc.__traceback__,
                                  file=sys.stderr)

    @staticmethod
    def log(message):
        """Log a message to stderr."""
        print(message, file=sys.stderr)
