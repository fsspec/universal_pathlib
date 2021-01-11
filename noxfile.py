import nox


@nox.session(python=False)
def develop(session):
    session.install("flit")
    session.run(*"flit install -s".split())


@nox.session(python=False)
def install(session):
    session.install(".")


@nox.session(reuse_venv=True)
def test(session):
    session.install(*"pytest".split())
    session.install(*".[test] --no-deps".split())
    session.run("pytest")
