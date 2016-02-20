"""Abstract out the host implementations to prevent tight coupling.

This makes it easier to swap out parts of the cade without affecting other
sections, making it easy to change hosts when needs change. As a side-effect,
this also makes forks with different backend needs easier to manage as they
will only need to change this file and add their own implementations to their
fork.
"""
from .bpo import Host as CLAHost
from .github import Host as ContribHost
from .heroku import Host as ServerHost
