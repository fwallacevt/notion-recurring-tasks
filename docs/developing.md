# Development setup

Walks you through how to setup your development environment to work with this repository.

## Visual Studio Code setup

If you haven't already, intall [Visual Studio Code](https://code.visualstudio.com/download). Make sure it's installed in
the `/Applications` directory on MacOS. _You may have to install `code` in `PATH`_ - see [here](https://stackoverflow.com/questions/29955500/code-not-working-in-command-line-for-visual-studio-code-on-osx-mac/39604469#39604469).

Next, hit `Cmd + Shift + X` to install extensions, and install the following:

- GitLens
- markdownlint
- Prettier
- Pylance
- Python
- Rewrap

## Installing requirements

### Cloning the code base

Now that you have vscode, you can clone the repository and begin working! Open the
[repository](https://github.com/fwallacevt/notion-recurring-tasks/), click the green button labeled "Code", click SSH,
and copy the provided address.

Then, from a terminal, run:

```sh
cd ~/
mkdir notion-recurring-tasks
git clone $SSH_ADDRESS_HERE
cd notion-recurring-tasks
code .
```

### Installing Python and Pipenv

Next, install xcode command line tools (sometimes a full xcode app install may be required):

```sh
xcode-select --install
```

We use [`pyenv` to manage Python versions, and `pipenv` to manage
dependencies](https://hackernoon.com/reaching-python-development-nirvana-bb5692adf30c). Install `pyenv` by running:

```sh
brew install pyenv
```

Next, we have to make sure we have the right version of Python installed. Check the [Pipfile](../Pipfile) to see what
version is expected, then run:

```sh
pyenv versions
```

If you don't see the expected version, run:

```sh
pyenv install $VERSION
```

Install `pipenv`:

```sh
pip3 install -U pipenv
```

## Setting up the development environment

You're finally ready to setup the development environment! From `notion-recurring-tasks`, run:

```sh
# Initiate a virtual environment if one doesn't exist, and open a shell inside it
pipenv shell
# Install all production and development requirements in Pipfile
pipenv install -d
```

_*It is critical that you work from within your viritual environment (`pipenv shell`) when developing*_.

## Running tests

As you're making changes, make sure to add additional test coverage and run tests to ensure you're not breaking existing
functionality. We use [pytest](https://docs.pytest.org/en/6.2.x/) to test our code. To run all tests, from within your
virtual environment simply run:

```sh
pytest --log-level=debug --capture=no
```

To run tests in parallel, you may add `-n $NUM`, where `$NUM` is the number of threads to use (utilizes `pytest-xdist`):

```sh
pytest -n $NUM --log-level=debug --capture=no
```

To run a single test suite, use the file path:

```sh
env pytest --log-level=debug --capture=no tests/path/to/test.py
```

To run a single test, use the path plus the name of the test:

```sh
env pytest --log-level=debug --capture=no tests/path/to/test.py::my_test_name
```

## Committing code

If you have not run `black` or `isort`, then your code will fail in CI. You must run `pipenv run format` before you
commit your code.
