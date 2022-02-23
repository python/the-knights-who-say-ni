# Contributing to `the-knights-who-say-ni`

## Code of Conduct
Work done surrounding this project is governed by the
[PSF Code of Conduct](https://www.python.org/psf/codeofconduct/).

## Dependencies
The `requirements.txt` file is frozen to the currently tested
versions of `requirements.in`. To update, create a venv,
install [`pip-tools`](https://pypi.org/project/pip-tools)
run `python3 -m pip-sync`, run all tests, and then update 
`requirements.txt` with `python3 -m pip-compile --upgrade` command.
Execute `python3 -m pip-sync` command and run tests once again
to make sure everything still works as expected.

## Testing
### Running tests
On a UNIX-based OS, simply run `test.sh`. On Windows, run
`test.bat`.

### Test coverage
Because of the legal importance of this project doing its job
correctly, 100% test coverage is always strived for.
