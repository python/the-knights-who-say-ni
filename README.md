# The Knights Who Say "Ni"!

The goal of this project is to provide a bot to annotate pull requests with whether their author has signed a CLA for the [Python project](https://github.com/python).

While written to work with [GitHub](https://github.com) and [bugs.python.org](http://bugs.python.org/) while hosted on [Heroku](https://www.heroku.com/), the design of the bot should be abstract enough to allow the pull request host (e.g., GitHub), the CLA record host (e.g., bugs.python.org), and the server host (e.g., Heroku) to be swapped out without much effort. The hope is that this bot can easily be forked by other projects with a need for a similar bot but whose components happen to differ.

## About the name
['The Knights Who Say "Ni!"'](https://www.youtube.com/watch?v=zIV4poUZAQo) is a sketch from the film, [Monty Python and the Holy Grail](https://en.wikipedia.org/wiki/Monty_Python_and_the_Holy_Grail). The knights prevent travelers from passing through their forest without a sacrifice (in the case of the film, it's their desire for a shrubbery). Since Python is actually named after Monty Python, it seemed fitting to have the project named after something originating from Monty Python relating to someone preventing something from occurring without being given something (in the film it's the knights requiring a shrubbery, in real life it's lawyers requiring a signed CLA).
