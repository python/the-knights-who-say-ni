# Abstract out the host implementations to prevent tight coupling.
from .bpo import Host as CLAHost
from .github import Host as ContribHost
from .heroku import Host as ServerHost
