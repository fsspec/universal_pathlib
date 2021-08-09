import os
import tempfile
from pathlib import Path
import subprocess
import shlex
import time
import sys


import pytest
from fsspec.implementations.local import LocalFileSystem
from fsspec.registry import register_implementation, _registry


def pytest_addoption(parser):
    parser.addoption(
        "--skiphdfs", action="store_true", default=False, help="skip hdfs tests"
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "hdfs: mark test as hdfs")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--skiphdfs"):
        return
    skip_hdfs = pytest.mark.skip(reason="skipping hdfs")
    for item in items:
        if "hdfs" in item.keywords:
            item.add_marker(skip_hdfs)


class DummyTestFS(LocalFileSystem):
    protocol = "mock"
    root_marker = "/"


@pytest.fixture(scope="session")
def clear_registry():
    register_implementation("mock", DummyTestFS)
    try:
        yield
    finally:
        _registry.clear()


@pytest.fixture()
def tempdir(clear_registry):
    with tempfile.TemporaryDirectory() as tempdir:
        yield tempdir


@pytest.fixture()
def local_testdir(tempdir, clear_registry):
    tmp = Path(tempdir)
    tmp.mkdir(exist_ok=True)
    folder1 = tmp.joinpath("folder1")
    folder1.mkdir()
    folder1_files = ["file1.txt", "file2.txt"]
    for f in folder1_files:
        p = folder1.joinpath(f)
        p.touch()
        p.write_text(f)

    file1 = tmp.joinpath("file1.txt")
    file1.touch()
    file1.write_text("hello world")
    file2 = tmp.joinpath("file2.txt")
    file2.touch()
    file2.write_bytes(b"hello world")
    if sys.platform.startswith("win"):
        yield str(Path(tempdir)).replace("\\", "/")
    else:
        yield tempdir


@pytest.fixture()
def pathlib_base(local_testdir):
    return Path(local_testdir)


@pytest.fixture(scope="session")
def htcluster():
    proc = subprocess.Popen(
        shlex.split("htcluster startup"),
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
    )
    time.sleep(30)
    yield
    proc.terminate()
    proc.wait()
    proc1 = subprocess.Popen(
        shlex.split("htcluster shutdown"),
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
    )
    proc1.terminate()
    proc1.wait()
    time.sleep(10)


@pytest.fixture()
def hdfs(htcluster, tempdir, local_testdir):
    pyarrow = pytest.importorskip("pyarrow")
    host, user, port = "0.0.0.0", "hdfs", 9000
    hdfs = pyarrow.hdfs.connect(host="0.0.0.0", port=9000, user=user)
    hdfs.mkdir(tempdir, create_parents=True)
    for x in Path(local_testdir).glob("**/*"):
        if x.is_file():
            text = x.read_text().encode("utf8")
            if not hdfs.exists(str(x.parent)):
                hdfs.mkdir(str(x.parent), create_parents=True)
            with hdfs.open(str(x), "wb") as f:
                f.write(text)
        else:
            hdfs.mkdir(str(x))
    hdfs.close()
    yield host, user, port


@pytest.fixture(scope="session")
def s3_server():
    # writable local S3 system
    if "BOTO_CONFIG" not in os.environ:  # pragma: no cover
        os.environ["BOTO_CONFIG"] = "/dev/null"
    if "AWS_ACCESS_KEY_ID" not in os.environ:  # pragma: no cover
        os.environ["AWS_ACCESS_KEY_ID"] = "foo"
    if "AWS_SECRET_ACCESS_KEY" not in os.environ:  # pragma: no cover
        os.environ["AWS_SECRET_ACCESS_KEY"] = "bar"
    requests = pytest.importorskip("requests")

    pytest.importorskip("moto")

    port = 5555
    endpoint_uri = "http://127.0.0.1:%s/" % port
    proc = subprocess.Popen(
        shlex.split("moto_server s3 -p %s" % port),
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
    )

    timeout = 5
    while timeout > 0:
        try:
            r = requests.get(endpoint_uri)
            if r.ok:
                break
        except Exception:  # pragma: no cover
            pass
        timeout -= 0.1  # pragma: no cover
        time.sleep(0.1)  # pragma: no cover
    anon = False
    s3so = dict(
        client_kwargs={"endpoint_url": endpoint_uri}, use_listings_cache=False
    )
    yield anon, s3so
    proc.terminate()
    proc.wait()


@pytest.fixture
def s3(s3_server, tempdir, local_testdir):
    s3fs = pytest.importorskip("s3fs")
    anon, s3so = s3_server
    s3 = s3fs.S3FileSystem(anon=False, **s3so)
    s3.mkdir(tempdir, create_parents=True)
    for x in Path(local_testdir).glob("**/*"):
        if x.is_file():
            text = x.read_text().encode("utf8")
            if not s3.exists(str(x.parent)):
                s3.mkdir(str(x.parent), create_parents=True)
            with s3.open(str(x), "wb") as f:
                f.write(text)
        else:
            s3.mkdir(str(x))
    yield anon, s3so
