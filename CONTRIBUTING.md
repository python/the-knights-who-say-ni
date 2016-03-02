# Contributing to `the-knights-who-say-ni`

## Code of Conduct
Work done surrounding this project is governed by the
[PSF Code of Conduct](https://www.python.org/psf/codeofconduct/).

## Dependencies
The `requirements.txt` file is frozen to the currently tested
versions of `requirements.base`. To update, create a venv,
run `python3 -m pip install -r requirements.base`, run all tests,
and then update `requirements.txt` with the output from `pip freeze`.

## Testing
### Running tests
On a UNIX-based OS, simply run `test.sh`. On Windows, run
`test.bat`.

### Test coverage
Because of the legal importance of this project doing its job
correctly, 100% test coverage is always strived for.
