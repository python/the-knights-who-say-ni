# The Knights Who Say "Ni"!
A bot to check if a contributor to a
[Python project](https://github.com/python) has signed the
[PSF CLA](https://www.python.org/psf/contrib/contrib-form/).

[![Build Status](https://travis-ci.org/python/the-knights-who-say-ni.svg?branch=master)](https://travis-ci.org/python/the-knights-who-say-ni)

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
means the Python project has some legal ground to stand on when it says
it didn't mean to use any patented code. Obviously this is all a pain
to deal with, but it's better to be safe than sorry.

But beyond just making sure the PSF is in the legal clear if bad code
is given to the Python project, it also helps make sure others who
use code from the Python project are also in the clear. If a company
wants to use Python code in a commercial fashion, having the Python
project's code covered by CLAs means they don't have to worry about
being sued as well.

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
working again.

Lastly, the master branch of this project will always strive to be
**stable and properly tested**. Because there are legal
ramifications if this project is unable to perform its duties, it is
imperative that it always function properly.

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
necessary for your own needs.

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
