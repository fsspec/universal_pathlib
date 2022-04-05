import os
import tempfile
from pathlib import Path
import subprocess
import shlex
import time
import sys
import datetime
from gcsfs.core import GCSFileSystem
import docker
from azure.storage.blob import BlobServiceClient

import pytest
from fsspec.implementations.local import LocalFileSystem
from fsspec.registry import register_implementation, _registry

import fsspec
import requests

AZURITE_URL = "http://127.0.0.1:10000"
ACCOUNT_NAME = "devstoreaccount1"
KEY = "Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw=="  # NOQA
CONNECTION_STRING = f"DefaultEndpointsProtocol=http;AccountName={ACCOUNT_NAME};AccountKey={KEY};BlobEndpoint={AZURITE_URL}/{ACCOUNT_NAME};"  # NOQA
data = b"0123456789"
metadata = {"meta": "data"}


def pytest_addoption(parser):
    parser.addoption(
        "--skiphdfs", action="store_true", default=False, help="skip hdfs tests"
    )

    parser.addoption(
        "--azurite",
        action="store_true",
        default=AZURITE_URL,
        help="azure blob storage host",
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


@pytest.fixture(scope="function")
def tempdir(clear_registry):
    with tempfile.TemporaryDirectory() as tempdir:
        yield tempdir


@pytest.fixture(scope="function")
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
        client_kwargs={"endpoint_url": endpoint_uri}, use_listings_cache=True
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


def stop_docker(container):
    cmd = shlex.split('docker ps -a -q --filter "name=%s"' % container)
    cid = subprocess.check_output(cmd).strip().decode()
    if cid:
        subprocess.call(["docker", "rm", "-f", "-v", cid])


TEST_PROJECT = os.environ.get("GCSFS_TEST_PROJECT", "test_project")


@pytest.fixture(scope="module")
def docker_gcs():
    if "STORAGE_EMULATOR_HOST" in os.environ:
        # assume using real API or otherwise have a server already set up
        yield os.environ["STORAGE_EMULATOR_HOST"]
        return
    container = "gcsfs_test"
    cmd = (
        "docker run -d -p 4443:4443 --name gcsfs_test fsouza/fake-gcs-server:latest -scheme "  # noqa: E501
        "http -public-host http://localhost:4443 -external-url http://localhost:4443"  # noqa: E501
    )
    stop_docker(container)
    subprocess.check_output(shlex.split(cmd))
    url = "http://0.0.0.0:4443"
    timeout = 10
    while True:
        try:
            r = requests.get(url + "/storage/v1/b")
            if r.ok:
                print("url: ", url)
                yield url
                break
        except Exception as e:  # noqa: E722
            timeout -= 1
            if timeout < 0:
                raise SystemError from e
            time.sleep(1)
    stop_docker(container)


@pytest.fixture
def gcs(docker_gcs, tempdir, local_testdir, populate=True):
    # from gcsfs.credentials import GoogleCredentials
    GCSFileSystem.clear_instance_cache()
    gcs = fsspec.filesystem("gcs", endpoint_url=docker_gcs)
    try:
        # ensure we're empty.
        try:
            gcs.rm("tmp", recursive=True)
        except FileNotFoundError:
            pass
        try:
            gcs.mkdir("tmp")
            print("made tmp dir")
        except Exception:
            pass
        if populate:
            for x in Path(local_testdir).glob("**/*"):
                if x.is_file():
                    gcs.upload(str(x), str(x))
                else:
                    gcs.mkdir(str(x))
        gcs.invalidate_cache()
        yield docker_gcs
    finally:
        try:
            gcs.rm(gcs.find("tmp"))
        except:  # noqa: E722
            pass


@pytest.fixture(scope="session")
def azurite(request):
    print(f'azurite host: {request.config.getoption("--azurite")}')
    return request.config.getoption("--azurite")


@pytest.fixture(scope="session")
def azurite_storage(azurite):

    """Copied from https://github.com/fsspec/adlfs/blob/master/adlfs/tests/conftest.py"""

    conn_str = f"DefaultEndpointsProtocol=http;AccountName={ACCOUNT_NAME};AccountKey={KEY};BlobEndpoint={AZURITE_URL}/{ACCOUNT_NAME};"  # NOQA

    bbs = BlobServiceClient.from_connection_string(conn_str=conn_str)
    bbs.create_container("data")
    container_client = bbs.get_container_client(container="data")
    bbs.insert_time = datetime.datetime.now(datetime.timezone.utc).replace(
        microsecond=0, tzinfo=datetime.timezone.utc
    )
    container_client.upload_blob("root/file1.txt", data)
    container_client.upload_blob("root/file2.txt", data)
    container_client.upload_blob("root/rfile.txt", data)
    container_client.upload_blob("root/a/file.txt", data)
    container_client.upload_blob("root/a1/file1.txt", data)
    container_client.upload_blob("root/b/file.txt", data)
    container_client.upload_blob("root/c/file1.txt", data)
    container_client.upload_blob("root/c/file2.txt", data)
    container_client.upload_blob(
        "root/d/file_with_metadata.txt", data, metadata=metadata
    )
    container_client.upload_blob("root/e+f/file1.txt", data)
    container_client.upload_blob("root/e+f/file2.txt", data)
    yield bbs


@pytest.fixture(scope="session", autouse=True)
def spawn_azurite():
    """Copied from https://github.com/fsspec/adlfs/blob/master/adlfs/tests/conftest.py"""
    print("Starting azurite docker container")
    client = docker.from_env()
    azurite = client.containers.run(
        "mcr.microsoft.com/azure-storage/azurite",
        "azurite-blob --loose --blobHost 0.0.0.0",
        detach=True,
        ports={"10000": "10000"},
    )
    print("Successfully created azurite container...")
    yield azurite
    print("Teardown azurite docker container")
    azurite.stop()
