import os
import shlex
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

import fsspec
import pytest
from fsspec.implementations.local import LocalFileSystem
from fsspec.registry import _registry
from fsspec.registry import register_implementation

from .utils import posixify


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
def local_testdir(tmp_path, clear_registry):
    folder1 = tmp_path.joinpath("folder1")
    folder1.mkdir()
    folder1_files = ["file1.txt", "file2.txt"]
    for f in folder1_files:
        p = folder1.joinpath(f)
        p.touch()
        p.write_text(f)

    file1 = tmp_path.joinpath("file1.txt")
    file1.touch()
    file1.write_text("hello world")
    file2 = tmp_path.joinpath("file2.txt")
    file2.touch()
    file2.write_bytes(b"hello world")
    if sys.platform.startswith("win"):
        yield str(tmp_path).replace("\\", "/")
    else:
        yield str(tmp_path)


@pytest.fixture()
def pathlib_base(local_testdir):
    return Path(local_testdir)


@pytest.fixture(scope="session")
def htcluster():
    try:
        proc = subprocess.Popen(
            shlex.split("htcluster startup"),
            stderr=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
        )
    except FileNotFoundError as err:
        if err.errno == 2 and "htcluster" == err.filename:
            pytest.skip("htcluster not installed")
        raise

    time.sleep(30)
    try:
        yield
    finally:
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
def hdfs(htcluster, tmp_path, local_testdir):
    pyarrow = pytest.importorskip("pyarrow")
    host, user, port = "0.0.0.0", "hdfs", 9000
    hdfs = pyarrow.hdfs.connect(host="0.0.0.0", port=9000, user=user)
    hdfs.mkdir(tmp_path, create_parents=True)
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
        os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    if "AWS_SECRET_ACCESS_KEY" not in os.environ:  # pragma: no cover
        os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    if "AWS_SECURITY_TOKEN" not in os.environ:  # pragma: no cover
        os.environ["AWS_SECURITY_TOKEN"] = "testing"
    if "AWS_SESSION_TOKEN" not in os.environ:  # pragma: no cover
        os.environ["AWS_SESSION_TOKEN"] = "testing"
    if "AWS_DEFAULT_REGION" not in os.environ:  # pragma: no cover
        os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    requests = pytest.importorskip("requests")

    pytest.importorskip("moto")

    port = 5555
    endpoint_uri = f"http://127.0.0.1:{port}/"
    proc = subprocess.Popen(
        shlex.split(f"moto_server s3 -p {port}"),
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
    )
    try:
        timeout = 5
        while timeout > 0:
            try:
                r = requests.get(endpoint_uri, timeout=10)
                if r.ok:
                    break
            except Exception:  # pragma: no cover
                pass
            timeout -= 0.1  # pragma: no cover
            time.sleep(0.1)  # pragma: no cover
        anon = False
        s3so = {
            "client_kwargs": {"endpoint_url": endpoint_uri},
            "use_listings_cache": True,
        }
        yield anon, s3so
    finally:
        proc.terminate()
        proc.wait()


@pytest.fixture
def s3_fixture(s3_server, local_testdir):
    pytest.importorskip("s3fs")
    anon, s3so = s3_server
    s3 = fsspec.filesystem("s3", anon=False, **s3so)
    bucket_name = "test_bucket"
    if s3.exists(bucket_name):
        for dir, _, keys in s3.walk(bucket_name):
            for key in keys:
                s3.rm(f"{dir}/{key}")
    else:
        s3.mkdir(bucket_name)
    for x in Path(local_testdir).glob("**/*"):
        target_path = f"{bucket_name}/{posixify(x.relative_to(local_testdir))}"
        if x.is_file():
            s3.upload(str(x), target_path)
    s3.invalidate_cache()
    yield f"s3://{bucket_name}", anon, s3so


def stop_docker(container):
    cmd = shlex.split('docker ps -a -q --filter "name=%s"' % container)
    cid = subprocess.check_output(cmd).strip().decode()
    if cid:
        subprocess.call(["docker", "rm", "-f", "-v", cid])


@pytest.fixture(scope="session")
def docker_gcs():
    if "STORAGE_EMULATOR_HOST" in os.environ:
        # assume using real API or otherwise have a server already set up
        yield os.environ["STORAGE_EMULATOR_HOST"]
        return

    requests = pytest.importorskip("requests")
    if shutil.which("docker") is None:
        pytest.skip("docker not installed")

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
            r = requests.get(url + "/storage/v1/b", timeout=10)
            if r.ok:
                yield url
                break
        except Exception as e:  # noqa: E722
            timeout -= 1
            if timeout < 0:
                raise SystemError from e
            time.sleep(1)
    stop_docker(container)


@pytest.fixture
def gcs_fixture(docker_gcs, local_testdir):
    pytest.importorskip("gcsfs")
    gcs = fsspec.filesystem("gcs", endpoint_url=docker_gcs)
    bucket_name = "test_bucket"
    if gcs.exists(bucket_name):
        for dir, _, keys in gcs.walk(bucket_name):
            for key in keys:
                gcs.rm(f"{dir}/{key}")
    else:
        gcs.mkdir(bucket_name)
    for x in Path(local_testdir).glob("**/*"):
        target_path = f"{bucket_name}/{posixify(x.relative_to(local_testdir))}"
        if x.is_file():
            gcs.upload(str(x), target_path)
    gcs.invalidate_cache()
    yield f"gs://{bucket_name}", docker_gcs


@pytest.fixture(scope="session")
def http_server(tmp_path_factory):
    http_tempdir = tmp_path_factory.mktemp("http")

    requests = pytest.importorskip("requests")
    pytest.importorskip("http.server")
    proc = subprocess.Popen(
        shlex.split(f"python -m http.server --directory {http_tempdir} 8080")
    )
    try:
        url = "http://127.0.0.1:8080/folder"
        path = Path(http_tempdir) / "folder"
        path.mkdir()
        timeout = 10
        while True:
            try:
                r = requests.get(url, timeout=10)
                if r.ok:
                    yield path, url
                    break
            except Exception as e:  # noqa: E722
                timeout -= 1
                if timeout < 0:
                    raise SystemError from e
                time.sleep(1)
    finally:
        proc.terminate()
        proc.wait()


@pytest.fixture
def http_fixture(local_testdir, http_server):
    http_path, http_url = http_server
    shutil.rmtree(http_path)
    shutil.copytree(local_testdir, http_path)
    yield http_url


@pytest.fixture(scope="session")
def webdav_server(tmp_path_factory):
    try:
        from cheroot import wsgi
        from wsgidav.wsgidav_app import WsgiDAVApp
    except ImportError as err:
        pytest.skip(str(err))

    webdav_tmp_dir = str(tmp_path_factory.mktemp("webdav"))

    host = "127.0.0.1"
    port = 8090
    app = WsgiDAVApp(
        {
            "host": host,
            "port": port,
            "provider_mapping": {"/": webdav_tmp_dir},
            "simple_dc": {"user_mapping": {"*": {"USER": {"password": "PASSWORD"}}}},
        }
    )
    srvr = wsgi.Server(bind_addr=(host, port), wsgi_app=app)
    srvr.prepare()
    thread = threading.Thread(target=srvr.serve, daemon=True)
    thread.start()

    try:
        yield f"webdav+http://{host}:{port}", app
    finally:
        srvr.stop()


@pytest.fixture
def webdav_fixture(local_testdir, webdav_server):
    webdav_url, app = webdav_server
    # switch to new test directory
    fs_provider = app.provider_map["/"]
    fs_provider.root_folder_path = os.path.abspath(local_testdir)
    try:
        yield webdav_url
    finally:
        # clear locks if any are held
        fs_provider.lock_manager.storage.clear()


@pytest.fixture(scope="session")
def azurite_credentials():
    url = "http://localhost:10000"
    account_name = "devstoreaccount1"
    key = "Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw=="  # noqa: E501
    endpoint = f"{url}/{account_name}"
    connection_string = f"DefaultEndpointsProtocol=http;AccountName={account_name};AccountKey={key};BlobEndpoint={endpoint};"  # noqa

    yield account_name, connection_string


@pytest.fixture(scope="session")
def docker_azurite(azurite_credentials):
    requests = pytest.importorskip("requests")

    if shutil.which("docker") is None:
        pytest.skip("docker not installed")

    image = "mcr.microsoft.com/azure-storage/azurite"
    container_name = "azure_test"
    cmd = (
        f"docker run --rm -d -p 10000:10000 --name {container_name} {image}"  # noqa: E501
        " azurite-blob --loose --blobHost 0.0.0.0"  # noqa: E501
    )
    url = "http://localhost:10000"

    stop_docker(container_name)
    subprocess.run(shlex.split(cmd), check=True)

    retries = 10
    while True:
        try:
            # wait until the container is up, even a 400 status code is ok
            r = requests.get(url, timeout=10)
            if (
                r.status_code == 400
                and "Server" in r.headers
                and "Azurite" in r.headers["Server"]
            ):
                yield url
                break
        except Exception as e:  # noqa: E722
            retries -= 1
            if retries < 0:
                raise SystemError from e
            time.sleep(1)

    stop_docker(container_name)


@pytest.fixture(scope="session")
def azure_container(azurite_credentials, docker_azurite):
    azure_storage = pytest.importorskip("azure.storage.blob")
    account_name, connection_string = azurite_credentials
    client = azure_storage.BlobServiceClient.from_connection_string(
        conn_str=connection_string
    )
    container_name = str(uuid.uuid4())
    client.create_container(container_name)

    try:
        yield container_name
    finally:
        client.delete_container(container_name)


@pytest.fixture(scope="function")
def azure_fixture(azurite_credentials, azure_container):
    azure_storage = pytest.importorskip("azure.storage.blob")
    account_name, connection_string = azurite_credentials
    client = azure_storage.BlobServiceClient.from_connection_string(
        conn_str=connection_string
    ).get_container_client(azure_container)

    try:
        yield f"az://{azure_container}"
    finally:
        for blob in client.list_blobs():
            client.delete_blob(blob["name"])
