# The Knights Who Say "Ni"!
A bot to check if a contributor to the the
[Python project](https://github.com/python) has signed a contributor
license agreement (CLA; an example of a CLA is the
[PSF CLA](https://www.python.org/psf/contrib/contrib-form/)).

## Why is this project necessary?
A CLA is necessary to make sure that someone contributing to an
open source project swears that they are only giving the project code
which they have the right to give away. This means that there are no
copyrights on the code from somewhere else, nor are there patents
making the use of the code illegal. This is really important for open
source projects like Python where the non-profit behind the
organization -- the
[Python Software Foundation](https://www.python.org/psf-landing/) in
Python's case -- do not have the money to pay off a patent troll if a
mistake is made and patented code is contributed. Basically a CLA
means the Python project has someone to legally blame if some code
was given to the project that it shouldn't have ever received.
Obviously this is all a pain to deal with, but it's better to be safe
than sorry.

But beyond just making sure the PSF is in the legal clear if bad code
is given to the Python project, it also helps make sure others who
use code from the Python project are also in the clear. If a company
wants to use Python code in a commercial fashion, having the Python
project's code covered by CLAs means they don't have to worry about
being sued as well. Hence it becomes much easier for the Python
project's code to be used widely by companies because they don't have
to worry about being sued themselves.

## Design goals
A CLA bot breaks down into essentially three components:

1. The server host
2. The contribution host
3. The CLA records host

In the case of the Python project and this bot, the server host is
[Heroku](https://www.heroku.com/), the contribution host is
[GitHub](https://github.com), and the CLA records host is
[bugs.python.org](http://bugs.python.org/) (which is an installation
of [Roundup](http://roundup.sourceforge.net/)). But considering the
Python project was started back in 1990 and has already changed
contribution hosts at least three times, a design goal of this
project is to try and
**abstract the hosting platforms** so that when the next change to
the Python project's relevant hosting platform occurs it will not
require a full rewrite of this project to get CLA enforcement
working.

Being a self-contained server app of low complexity, another design
goal is for this project to act as a
**stellar example of a Python server project** for the latest release
of Python.

Lastly, the master branch of this project will always strive to be
**stable and be properly tested**. Because there are legal
ramifications if this project is unable to perform its duties, it is
imperative that it function properly. (This design goal
will not be enforced until the project is considered ready for
deployment.)

### Why wasn't some pre-existing CLA bot used?
There are several other CLA enforcement projects and services
available, such as [clabot](https://github.com/clabot/clabot),
[CLA Enforcer](https://github.com/datastax/cla-enforcer),
[CLAHub](https://github.com/clahub/clahub), and
[CLA Assistant](https://cla-assistant.io/). The issue with all of
these project is that they are either unmaintained or they make
assumptions about where/how CLAs are stored (e.g., they require
using [DocuSign](https://www.docusign.ca/)). Because of these issues
and the fact that this is an important project for Python itself, it
was deemed necessary to create our own CLA enforcement bot which the
Python project controlled and was able to make sure was maintained.

### Is this project useful to anyone besides the Python project?
While this project is, strictly speaking, geared towards the needs of
the Python project, the abstraction design goal should make it
relatively straight-forward to fork this project and to modify it as
necessary for your own needs. The project would also be amenable to
tweaking APIs and such to add needed flexibility for forks. There is
also the potential to even merge alternative host implementations
if a fork of this project with a different host implementation(s)
were to come into existence.

## Control flow
The key piece of legal information one must know is that the instant
code is provided to the Python project, it is considered contributed.
That means it is critical to prevent accepting that contribution if
the contributor has not signed the CLA. What this means is that
once a person has signed the CLA, their contribution is considered in
the clear and thus does not need to be checked again to see if
they have rescinded their CLA (if that does happen then only future
contributions which they have not yet made will not be covered by
their original CLA).

All of this leads to the following pseuodcode under GitHub:

```python3
if pull_request.is_opened:
    usernames = pull_request.committers
    if signed_cla(username):
        pull_request.add_label(OK)
    else:
        pull_request.add_label(no_CLA)
        # "No CLA" can either be from no GitHub account found on
        # bugs.python.org or because they have not signed the CLA.
        pull_request.add_comment(why_no_CLA)
elif pull_request.label_removed:
    if pull_request.label_removed in CLA_labels:
    # Removing a CLA label triggers the bot to check for CLAs again.
    usernames = pull_request.committers
    if signed_cla(username):
        pull_request.add_label(OK)
    else:
        # The assumption is that if the check is being triggered
        # again and there is no CLA then the pull request most likely
        # started off w/o a CLA and thus got the message to begin
        # with.
        pull_request.add_label(no_CLA)
elif pull_request.synchronized:  # Code updated.
    usernames = pull_request.committers
    old_cla_label = pull_request.cla_label()
    if usernames == [pull_request.author] and old_cla_label == CLA_OK:
        # No name to check again as we already cleared this pull request.
        # This is an optimization to lower load on bugs.python.org and may
        # not be worth it.
        pass
    elif signed_cla(usernames) and old_cla_label == no_CLA:
        # The unlabeling will trigger the bot for the label removal.
        pull_request.remove_bad_labels()
    elif not signed_cla(usernames) and old_cla_label == CLA_OK:
        pull_request.remove_bad_labels()
```

## About the project's name
['The Knights Who Say "Ni!"'](https://www.youtube.com/watch?v=zIV4poUZAQo)
is a sketch from the film,
[Monty Python and the Holy Grail](https://en.wikipedia.org/wiki/Monty_Python_and_the_Holy_Grail).
The knights prevent travelers from passing through their forest
without a sacrifice (in the case of the film, they demand a
shrubbery). Since Python is actually named after Monty Python, it
seemed fitting to have the project named after something originating
from Monty Python relating to someone preventing something from
occurring without being given something (in the film it's the knights
requiring a shrubbery, in real life it's lawyers requiring a signed
CLA).
