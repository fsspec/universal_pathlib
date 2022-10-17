import sys

import nox
from pathlib import Path


@nox.session()
def develop(session):
    session.install("flit")
    session.run(*"flit install -s".split())


@nox.session()
def black(session):
    session.install("black")
    session.run(*"black upath noxfile.py setup.py".split())


@nox.session()
def lint(session):
    session.install("flake8")
    session.run("flake8", "upath")


@nox.session()
def type_checking(session):
    session.install("mypy")
    session.run("mypy", "upath")


@nox.session()
def install(session):
    session.install(".")


@nox.session()
def smoke(session):
    if (3, 10) < sys.version_info <= (3, 11, 0, "final"):
        # workaround for missing aiohttp wheels for py3.11
        session.install(
            "aiohttp",
            "--no-binary",
            "aiohttp",
            env={"AIOHTTP_NO_EXTENSIONS": "1"},
        )

    session.install(
        "pytest",
        "adlfs",
        "aiohttp",
        "requests",
        "gcsfs",
        "s3fs",
        "moto[s3,server]",
        "webdav4[fsspec]",
        "wsgidav",
        "cheroot",
    )
    session.run(*"pytest --skiphdfs -vv upath".split())


@nox.session()
def build(session):
    session.install("flit")
    session.run(*"flit build".split())


@nox.session()
def rm_dirs(session):
    paths = ["build", "dist"]
    for path in paths:
        p = Path(path)
        if p.exists():
            session.run(*f"rm -rf {str(p)}".split())
