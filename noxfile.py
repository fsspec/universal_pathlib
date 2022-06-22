import nox
from pathlib import Path


@nox.session(python=False)
def develop(session):
    session.install("flit")
    session.run(*"flit install -s".split())


@nox.session(python=False)
def black(session):
    session.install("black")
    session.run(*"black upath noxfile.py setup.py".split())


@nox.session(python=False)
def lint(session):
    session.install("flake8")
    session.run(*"flake8".split())


@nox.session(python=False)
def install(session):
    session.install(".")


@nox.session(python=False)
def smoke(session):
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


@nox.session(python=False)
def build(session):
    session.install("flit")
    session.run(*"flit build".split())


@nox.session(python=False)
def rm_dirs(session):
    paths = ["build", "dist"]
    for path in paths:
        p = Path(path)
        if p.exists():
            session.run(*f"rm -rf {str(p)}".split())
