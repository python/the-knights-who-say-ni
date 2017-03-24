import os
import sys
import traceback
from typing import Optional

from . import abc as ni_abc


class Host(ni_abc.ServerHost):

    """Server hosting on Heroku."""

    @staticmethod
    def port() -> int:
        return int(os.environ['PORT'])

    @staticmethod
    def contrib_auth_token() -> str:
        return os.environ['GH_AUTH_TOKEN']

    @staticmethod
    def contrib_secret() -> str:
        return os.environ["GH_SECRET"]

    @staticmethod
    def user_agent() -> Optional[str]:
        return os.environ.get('USER_AGENT')

    def log_exception(self, exc: BaseException) -> None:
        """Log an exception and its traceback to stderr."""
        traceback.print_exception(type(exc), exc, exc.__traceback__,
                                  file=sys.stderr)

    def log(self, message: str) -> None:
        """Log a message to stderr."""
        print(message, file=sys.stderr)
