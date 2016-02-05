import os

from . import abc


class Host(abc.ServerHost):

    """Server hosting on Heroku."""

    def port(self):
        return int(os.environ['PORT'])