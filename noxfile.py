import nox


@nox.session(python=False)
def develop(session):
    session.install("flit")
    session.run(*"flit install -s".split())


@nox.session(python=False)
def black(session):
    session.install("black")
    session.run(*"black upath".split())


@nox.session(python=False)
def lint(session):
    session.install("flake8")
    session.run(*"flake8 upath".split())


@nox.session(python=False)
def install(session):
    session.install(".")


@nox.session(python=False)
def smoke(session):
    session.install(*"pytest".split())
    session.run(*"pytest --skiphdfs upath".split())


@nox.session(python=False)
def build(session):
    session.install("flit")
    session.run(*"flit build".split())
