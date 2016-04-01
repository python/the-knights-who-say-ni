import json
from . import abc


class Host(abc.CLAHost):

    """CLA record hosting at bugs.python.org."""

    async def check(self, usernames):
        base_url = "http://bugs.python.org/user?@template=clacheck&github_names="
        url = base_url + ','.join(usernames)
        async with abc.session().get(url) as response:
            if response.status >= 300:
                msg = 'unexpected response for {!r}: {}'.format(response.url,
                                                                response.status)
                raise client.HTTPException(msg)
            # Explicitly decode JSON as b.p.o doesn't set the content-type as
            # `application/json`.
            results = json.loads(await response.text())
        if all(results.values()):
            return abc.Status.signed
        elif any(value is None for value in results.values()):
            return abc.Status.username_not_found
        else:
            return abc.Status.not_signed
