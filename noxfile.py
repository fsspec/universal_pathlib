"""Automation using nox."""

import glob
import os
import sys

import nox

nox.options.reuse_existing_virtualenvs = True
nox.options.error_on_external_run = True

nox.needs_version = ">=2024.04.15"
nox.options.default_venv_backend = "uv"

nox.options.sessions = "lint", "tests", "type-checking", "type-safety"
locations = ("upath",)
running_in_ci = os.environ.get("CI", "") != ""

SUPPORTED_PYTHONS = ["3.9", "3.10", "3.11", "3.12", "3.13", "3.14"]
BASE_PYTHON = SUPPORTED_PYTHONS[-3]
MIN_PYTHON = SUPPORTED_PYTHONS[0]


@(lambda f: f())
def FSSPEC_MIN_VERSION() -> str:
    """Get the minimum fsspec version boundary from pyproject.toml."""
    try:
        from packaging.requirements import Requirement

        if sys.version_info >= (3, 11):
            from tomllib import load as toml_load
        else:
            from tomli import load as toml_load
    except ImportError:
        raise RuntimeError(
            "We rely on nox>=2024.04.15 depending on `packaging` and `tomli/tomllib`."
            " Please report if you see this error."
        )

    with open("pyproject.toml", "rb") as f:
        pyproject_data = toml_load(f)

    for requirement in pyproject_data["project"]["dependencies"]:
        req = Requirement(requirement)
        if req.name == "fsspec":
            for specifier in req.specifier:
                if specifier.operator == ">=":
                    return str(specifier.version)
    raise RuntimeError("Could not find fsspec minimum version in pyproject.toml")


@nox.session(python=SUPPORTED_PYTHONS)
def tests(session: nox.Session) -> None:
    """Run the test suite."""
    # workaround in case no aiohttp binary wheels are available
    if session.python == "3.14":
        session.env["AIOHTTP_NO_EXTENSIONS"] = "1"
        session.install(".[tests,dev]", "pydantic>=2.12.0a1")
    else:
        session.install(".[tests,dev,dev-third-party]")
    session.run("uv", "pip", "freeze", silent=not running_in_ci)
    session.run(
        "pytest",
        "-m",
        "not hdfs",
        "--cov",
        "--cov-config=pyproject.toml",
        *session.posargs,
        env={"COVERAGE_FILE": f".coverage.{session.python}"},
    )


@nox.session(python=MIN_PYTHON, name="tests-minversion")
def tests_minversion(session: nox.Session) -> None:
    session.install(f"fsspec=={FSSPEC_MIN_VERSION}", ".[tests,dev]")
    session.run("uv", "pip", "freeze", silent=not running_in_ci)
    session.run(
        "pytest",
        "-m",
        "not hdfs",
        "--cov",
        "--cov-config=pyproject.toml",
        *session.posargs,
        env={"COVERAGE_FILE": f".coverage.{session.python}"},
    )


tests_minversion.__doc__ = f"Run the test suite with fsspec=={FSSPEC_MIN_VERSION}."


@nox.session
def lint(session: nox.Session) -> None:
    """Run pre-commit hooks."""
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
    """Build sdists and wheels."""
    session.install("build", "setuptools", "twine")
    session.run("python", "-m", "build")
    dists = glob.glob("dist/*")
    session.run("twine", "check", *dists, silent=True)


@nox.session
def develop(session: nox.Session) -> None:
    """Sets up a python development environment for the project."""
    session.run("uv", "venv", external=True)


@nox.session(name="type-checking", python=BASE_PYTHON)
def type_checking(session):
    """Run mypy checks."""
    session.install("-e", ".[typechecking]")
    session.run("python", "-m", "mypy")


@nox.session(name="type-safety", python=SUPPORTED_PYTHONS)
def type_safety(session):
    """Run typesafety tests."""
    session.install("-e", ".[typechecking]")
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
        *session.posargs,
    )


@nox.session(name="flavours-upgrade-deps", python=BASE_PYTHON)
def upgrade_flavours(session):
    session.run("uvx", "pur", "-r", "dev/requirements.txt")


@nox.session(name="flavours-codegen", python=BASE_PYTHON)
def generate_flavours(session):
    session.install("-r", "dev/requirements.txt")
    with open("upath/_flavour_sources.py", "w") as target:
        session.run(
            "python",
            "dev/fsspec_inspector/generate_flavours.py",
            stdout=target,
            stderr=None,
        )


@nox.session(name="docs-build", python=BASE_PYTHON)
def docs_build(session):
    """Build the documentation in strict mode."""
    session.install("--group=docs", "-e", ".")
    session.run("mkdocs", "build")


@nox.session(name="docs-serve", python=BASE_PYTHON)
def docs_serve(session):
    """Serve the documentation with live reloading."""
    session.install("--group=docs", "-e", ".")
    session.run("mkdocs", "serve", "--no-strict")
