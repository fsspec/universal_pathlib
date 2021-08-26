import os
import tempfile
from pathlib import Path
import subprocess
import shlex
import time
import sys
from contextlib import contextmanager
from gcsfs.core import GCSFileSystem

import vcr.stubs.aiohttp_stubs as aios
import pytest
from fsspec.implementations.local import LocalFileSystem
from fsspec.registry import register_implementation, _registry
from upath.tests.utils import TEST_BUCKET, TEST_PROJECT, GOOGLE_TOKEN, RECORD_MODE, allfiles, gcs_maker


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

@pytest.fixture(scope="session")
def gcs():
    with gcs_maker() as gcs:  # TODO: should I add record mode here?
        yield gcs

        # # teardown after testing 
        # # remove all files in the bucket
        # file_list = gcs.find(TEST_BUCKET)
        # gcs.rm(file_list)
        # # remove the empty bucket
        # gcs.rmdir(TEST_BUCKET)

# patch; for some reason, original wants vcr_response["url"], which is empty
def build_response(vcr_request, vcr_response, history):
    request_info = aios.RequestInfo(
        url=aios.URL(vcr_request.url),
        method=vcr_request.method,
        headers=aios.CIMultiDictProxy(aios.CIMultiDict(vcr_request.headers)),
        real_url=aios.URL(vcr_request.url),
    )
    response = aios.MockClientResponse(
        vcr_request.method, aios.URL(vcr_request.url), request_info=request_info
    )
    response.status = vcr_response["status"]["code"]
    response._body = vcr_response["body"].get("string", b"")
    response.reason = vcr_response["status"]["message"]
    head = {
        k: v[0] if isinstance(v, list) else v
        for k, v in vcr_response["headers"].items()
    }
    response._headers = aios.CIMultiDictProxy(aios.CIMultiDict(head))
    response._history = tuple(history)

    response.close()
    return response


aios.build_response = build_response


# patch: but the value of body back in the stream, to enable streaming reads
# https://github.com/kevin1024/vcrpy/pull/509
async def record_response(cassette, vcr_request, response):
    """Record a VCR request-response chain to the cassette."""

    try:
        byts = await response.read()
        body = {"string": byts}
        if byts:
            if response.content._buffer_offset:
                response.content._buffer[0] = response.content._buffer[0][
                    response.content._buffer_offset :
                ]
                response.content._buffer_offset = 0
            response.content._size += len(byts)
            response.content._cursor -= len(byts)
            response.content._buffer.appendleft(byts)
            response.content._eof_counter = 0

    except aios.ClientConnectionError:
        body = {}

    vcr_response = {
        "status": {"code": response.status, "message": response.reason},
        "headers": aios._serialize_headers(response.headers),
        "body": body,  # NOQA: E999
        "url": str(response.url)
        .replace(TEST_BUCKET, "upath-testing")
        .replace(TEST_PROJECT, "test_project"),
    }

    cassette.append(vcr_request, vcr_response)


aios.record_response = record_response


def play_responses(cassette, vcr_request):
    history = []
    vcr_response = cassette.play_response(vcr_request)
    response = build_response(vcr_request, vcr_response, history)

    # If we're following redirects, continue playing until we reach
    # our final destination.
    while 300 <= response.status <= 399:
        if "Location" not in response.headers:
            # Not a redirect, an instruction not to call again
            break
        next_url = aios.URL(response.url).with_path(response.headers["location"])

        # Make a stub VCR request that we can then use to look up the recorded
        # VCR request saved to the cassette. This feels a little hacky and
        # may have edge cases based on the headers we're providing (e.g. if
        # there's a matcher that is used to filter by headers).
        vcr_request = aios.Request(
            "GET",
            str(next_url),
            None,
            aios._serialize_headers(response.request_info.headers),
        )
        vcr_request = cassette.find_requests_with_most_matches(vcr_request)[0][0]

        # Tack on the response we saw from the redirect into the history
        # list that is added on to the final response.
        history.append(response)
        vcr_response = aios.cassette.play_response(vcr_request)
        response = aios.build_response(vcr_request, vcr_response, history)

    return response


aios.play_responses = play_responses