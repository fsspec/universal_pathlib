"""Automation using nox."""

import glob
import os

import nox

nox.options.reuse_existing_virtualenvs = True
nox.options.sessions = "lint", "tests"
locations = ("upath",)


@nox.session(python=["3.8", "3.9", "3.10", "3.11", "3.12", "3.13"])
def tests(session: nox.Session) -> None:
    # workaround in case no aiohttp binary wheels are available
    session.env["AIOHTTP_NO_EXTENSIONS"] = "1"
    session.install(".[tests,dev]")
    session.run(
        "pytest",
        "-m",
        "not hdfs",
        "--cov",
        "--cov-config=pyproject.toml",
        *session.posargs,
        env={"COVERAGE_FILE": f".coverage.{session.python}"},
    )


@nox.session(python="3.8", name="tests-minversion")
def tests_minversion(session: nox.Session) -> None:
    session.install("fsspec==2022.1.0", ".[tests,dev]")
    session.run(
        "pytest",
        "-m",
        "not hdfs",
        "--cov",
        "--cov-config=pyproject.toml",
        *session.posargs,
        env={"COVERAGE_FILE": f".coverage.{session.python}"},
    )


@nox.session
def lint(session: nox.Session) -> None:
    session.install("pre-commit")
    session.install("-e", ".[tests]")

    args = *(session.posargs or ("--show-diff-on-failure",)), "--all-files"
    session.run("pre-commit", "run", *args)


@nox.session
def safety(session: nox.Session) -> None:
    """Scan dependencies for insecure packages."""
    session.install(".")
    session.install("safety")
    session.run("safety", "check", "--full-report")


@nox.session
def build(session: nox.Session) -> None:
    session.install("build", "setuptools", "twine")
    session.run("python", "-m", "build")
    dists = glob.glob("dist/*")
    session.run("twine", "check", *dists, silent=True)


@nox.session
def develop(session: nox.Session) -> None:
    """Sets up a python development environment for the project."""
    args = session.posargs or ("venv",)
    venv_dir = os.fsdecode(os.path.abspath(args[0]))

    session.log(f"Setting up virtual environment in {venv_dir}")
    session.install("virtualenv")
    session.run("virtualenv", venv_dir, silent=True)

    python = os.path.join(venv_dir, "bin/python")
    session.run(python, "-m", "pip", "install", "-e", ".[tests,dev]", external=True)


@nox.session
def black(session):
    print("please run `nox -s lint` instead")
    raise SystemExit(1)


@nox.session
def type_checking(session):
    session.install("-e", ".[tests]")
    session.run("python", "-m", "mypy")


@nox.session
def typesafety(session):
    session.install("-e", ".[tests]")
    session.run(
        "python",
        "-m",
        "pytest",
        "-v",
        "-p",
        "pytest-mypy-plugins",
        "--mypy-pyproject-toml-file",
        "pyproject.toml",
        "typesafety",
    )


@nox.session(python="3.12")
def generate_flavours(session):
    session.install("-r", "dev/requirements.txt")
    with open("upath/_flavour_sources.py", "w") as target:
        session.run(
            "python", "dev/fsspec_inspector/generate_flavours.py", stdout=target
        )
