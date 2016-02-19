from . import abc


class Host(abc.CLAHost):

    """CLA record hosting at bugs.python.org."""

    async def check(self, usernames):  # pragma: no cover
        # XXX Placeholder until b.p.o has an API to use.
        signed = {'brettcannon'}
        return abc.Status.signed if all(x in signed for x in usernames) else abc.Status.not_signed
