# Abstract out the host implementations to prevent tight coupling.
from .heroku import Host as ServerHost
from .github import Host as ContribHost
from .bpo import Host as CLAHost