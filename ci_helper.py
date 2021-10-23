#!/usr/bin/env python3
#
# Usage: python ci_helper.py

import subprocess
from os import environ


def run(cmd: str, *args: str):
    """Run a shell command and raise an error if it fails."""
    subprocess.run([cmd, *args], check=True)


def pipenv_run(cmd: str, *args: str):
    """Run a shell command inside the virtual environment created by `pipenv`.

    This should include all of our installed Python packages and CLI tools."""
    run("pipenv", "run", cmd, *args)


# Run the type checker.
pipenv_run("mypy", "--version")
pipenv_run("mypy", "--show-traceback", ".")

try:
    pipenv_run("isort", "--version")
    pipenv_run("check")
except Exception as e:
    print(
        "Failed formatting check; please run 'pipenv run format' and re-commit"
    )
    raise e


def pytest(*args: str):
    """Run pytest with the specified arguments."""
    pipenv_run(
        "pytest",
        "--log-level=debug",
        "--capture=no",
        "tests/utils/test_schedule.py::test_get_next_specific_days",
        *args,
    )


pytest(
    "--cov-config=.coveragerc",
    "--cov=.",
    "-n",
    "8",
    "--cov-report",
    "xml:../../test_output/test-output-model_train/coverage/cobertura-coverage.xml",
)
