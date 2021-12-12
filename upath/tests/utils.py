from contextlib import contextmanager
import gzip
import json
import os
import re
import pickle
from pathlib import Path

from gcsfs.core import GCSFileSystem

TEST_PROJECT = os.environ.get("GCSFS_TEST_PROJECT", "test_project")
TEST_BUCKET = os.environ.get("GCSFS_TEST_BUCKET", "upath_test")
TEST_BUCKET_2 = os.environ.get("GCSFS_TEST_BUCKET_2", "upath-testing-2")
RECORD_MODE = os.environ.get("GCSFS_RECORD_MODE", "none")
FAKE_TOKEN = {
    "access_token": "xxx",
    "expires_in": 0,
    "grant_type": "refresh_token",
    "refresh_token": "xxx",
    "timestamp": 1487859400.0,
}
not_secret = {
    "client_id": "586241054156-9kst7ltfj66svc342pcn43vp6ta3idin"
    ".apps.googleusercontent.com",
    "client_secret": "xto0LIFYX35mmHF9T1R2QBqT",
}
FAKE_TOKEN.update(not_secret)

FAKE_GOOGLE_TOKEN = {
    "client_id": (
        "764086051850-6qr4p6gpi6hn506pt8ejuq83di341hur."
        "apps.googleusercontent.com"
    ),
    "client_secret": "d-FL95Q19q7MQmFpd7hHD0Ty",
    "refresh_token": "xxx",
    "type": "authorized_user",
}
GOOGLE_TOKEN = os.environ.get("GCSFS_GOOGLE_TOKEN", FAKE_GOOGLE_TOKEN)
ON_VCR = "GCSFS_GOOGLE_TOKEN" not in os.environ

print('RECORD_MODE: ', RECORD_MODE)

if RECORD_MODE == "all":
    GOOGLE_TOKEN = "/home/andrew/Dropbox/Programming/universal_pathlib/upath-324916-43405b838929.json"
if isinstance(GOOGLE_TOKEN, str) and os.path.exists(GOOGLE_TOKEN):
    with open(GOOGLE_TOKEN) as f:
        GOOGLE_TOKEN = json.load(f)

# credentials used by the test suite in ci
# FAKE_GOOGLE_TOKEN = {
#     "client_id": (
#         "764086051850-6qr4p6gpi6hn506pt8ejuq83di341hur."
#         "apps.googleusercontent.com"
#     ),
#     "client_secret": "d-FL95Q19q7MQmFpd7hHD0Ty",
#     "refresh_token": "xxx",
#     "type": "authorized_user",
# }
# GOOGLE_TOKEN = os.environ.get("GCSFS_GOOGLE_TOKEN", FAKE_GOOGLE_TOKEN)
#  #    json.loads(
# #         Path("/home/andrew/Dropbox/Programming/universal_pathlib/upath-324916-43405b838929.json").read_text()
# #     )  # os.environ.get("GCSFS_GOOGLE_TOKEN", FAKE_GOOGLE_TOKEN)
# # )
# RECORD_MODE = os.environ.get("GCSFS_RECORD_MODE", "none")
# if RECORD_MODE=="none":
#     GOOGLE_TOKEN = FAKE_GOOGLE_TOKEN
# else:
#     GOOGLE_TOKEN = json.loads(
#         Path("/home/andrew/Dropbox/Programming/universal_pathlib/upath-324916-43405b838929.json").read_text()
#     )  # os.environ.get("GCSFS_GOOGLE_TOKEN", FAKE_GOOGLE_TOKEN)
# )

import vcr


def before_record_response(response):
    """
    Scrub the response of sensitive data and override with test creds.

    When creating the vcr recordings, any credentials and buckets can be
    used. This method will take whatever (valid) creds and gcs locations
    are used for creating the cassette and override it with the test
    parameters so that playback matches the test conditions.
    """
    r = pickle.loads(pickle.dumps(response))
    for field in ["Alt-Svc", "Date", "Expires", "X-GUploader-UploadID"]:
        r["headers"].pop(field, None)
    if "Location" in r["headers"]:
        loc = r["headers"]["Location"]
        if isinstance(loc, list):
            r["headers"]["Location"] = [
                r["headers"]["Location"][0]
                .replace(TEST_BUCKET, "upath_test")
                .replace(TEST_PROJECT, "test_project")
            ]
        else:
            r["headers"]["Location"] = loc.replace(
                TEST_BUCKET, "upath_test"
            ).replace(TEST_PROJECT, "test_project")
    try:
        try:
            data = json.loads(gzip.decompress(r["body"]["string"]).decode())
            if "access_token" in data:
                data["access_token"] = "xxx"
            if "id_token" in data:
                data["id_token"] = "xxx"
            if "refresh_token" in data:
                data["refresh_token"] = "xxx"
            if "expires_in" in data:
                data.pop("expires_in")
            # If comparing encoded string fails, dump it in a decoded form
            # to see which value has changed.
            r["body"]["string"] = gzip.compress(
                json.dumps(data)
                .replace(TEST_PROJECT, "test_project")
                .replace(TEST_BUCKET, "upath_test")
                .encode()
            )
        except (OSError, TypeError, ValueError):
            r["body"]["string"] = (
                r["body"]["string"]
                .replace(TEST_PROJECT.encode(), b"test_project")
                .replace(TEST_BUCKET.encode(), b"upath_test")
            )
    except Exception:
        pass
    return r


def before_record(request):
    """
    Scrub the request of sensitive data and override with test creds.

    When creating the vcr recordings, any credentials and buckets can be
    used. This method will take whatever (valid) creds and gcs locations
    are used for creating the cassette and override it with the test
    parameters so that playback matches the test conditions.
    """
    r = pickle.loads(pickle.dumps(request))
    print(r.body)
    for field in ["User-Agent"]:
        r.headers.pop(field, None)
    # modify the uri of the request
    # replace the project and bucket with test values
    r.uri = request.uri.replace(TEST_PROJECT, "test_project").replace(
        TEST_BUCKET, "upath_test"
    )
    # modify the body of the request
    if r.body:
        # replace all the fields in GOOGLE_TOKEN with xxx
        for field in GOOGLE_TOKEN:
            r.body = r.body.replace(GOOGLE_TOKEN[field].encode(), b"xxx")
        # replace the project and bucket with test values
        r.body = r.body.replace(TEST_PROJECT.encode(), b"test_project").replace(
            TEST_BUCKET.encode(), b"upath_test"
        )
        # ensure that refresh_token and assertion are set to xxx
        r.body = re.sub(b"refresh_token=[^&]+", b"refresh_token=xxx", r.body)
        r.body = re.sub(b"assertion=[^&]+", b"assertion=xxx", r.body)

    # import pdb; pdb.set_trace()
    print(r.body)
    return r


def matcher(r1, r2):
    """custom request matcher. determines when to use a cassette response

    each cassette has multiple request/response pairs. each request
    must match the cassette request. like a cassette tape, these
    are "played" in order. Thus, this method is checking each
    request in order as the request happens.

    r1=request, r2=stored request

    Returns True if the request matches the next request in the cassette"""
    # import pdb; pdb.set_trace()
    print("r1", r1)
    print("r2", r2)
    if (
        r2.uri.replace(TEST_PROJECT, "test_project").replace(
            TEST_BUCKET, "upath_test"
        )
        != r1.uri
    ):
        print("uris dont match when test proj and test buck replaced")
        return False
    if r1.method != r2.method:
        print("methods dont match")
        return False
    if r1.method != "POST" and r1.body != r2.body:
        print('r1.method != "POST" and r1.body != r2.body')
        return False
    if r1.method == "POST":
        if "upload_id" in r1.uri and "upload_id" in r2.uri:
            # vcrpy looses body on redirect with aiohttp
            if r2.body is None and int(r2.headers["Content-Length"]) > 1:
                r2.body = r1.body
        try:
            return json.loads(r2.body.decode()) == json.loads(r1.body.decode())
        except:  # noqa: E722
            pass
        print(r1.body)
        r1q = (r1.body or b"").split(b"&")
        r2q = (r2.body or b"").split(b"&")
        print("r1q", r1q)
        print("r2q")
        for qu in r1q:
            print(qu)
            if b"secret" in qu or b"token" in qu:
                continue
            if b"grant_type=refresh_token" in qu or b"client_id" in qu:
                continue
            if qu not in r2q:
                print("qu not in r2q")
                return False
    else:
        for key in ["Content-Length", "Content-Type", "Range"]:
            if key in r1.headers and key in r2.headers:
                if r1.headers.get(key, "") != r2.headers.get(key, ""):
                    print("last false")
                    return False
    print("\nMATCHER SUCCESS\n")
    print(f"{r1.body}\n{r2.body}\n\n")
    return True


recording_path = os.path.join(os.path.dirname(__file__), "recordings")

my_vcr = vcr.VCR(
    cassette_library_dir=recording_path,
    record_mode=RECORD_MODE,
    path_transformer=vcr.VCR.ensure_suffix(".yaml"),
    filter_headers=["Authorization"],
    filter_query_parameters=[
        "refresh_token",
        "client_id",
        "client_secret",
        "assertion",
    ],
    before_record_response=before_record_response,
    before_record=before_record,
)
my_vcr.register_matcher("all", matcher)
my_vcr.match_on = ["all"]
files = {
    "test/accounts.1.json": (
        b'{"amount": 100, "name": "Alice"}\n'
        b'{"amount": 200, "name": "Bob"}\n'
        b'{"amount": 300, "name": "Charlie"}\n'
        b'{"amount": 400, "name": "Dennis"}\n'
    ),
    "test/accounts.2.json": (
        b'{"amount": 500, "name": "Alice"}\n'
        b'{"amount": 600, "name": "Bob"}\n'
        b'{"amount": 700, "name": "Charlie"}\n'
        b'{"amount": 800, "name": "Dennis"}\n'
    ),
}

csv_files = {
    "2014-01-01.csv": (
        b"name,amount,id\n" b"Alice,100,1\n" b"Bob,200,2\n" b"Charlie,300,3\n"
    ),
    "2014-01-02.csv": b"name,amount,id\n",
    "2014-01-03.csv": (
        b"name,amount,id\n" b"Dennis,400,4\n" b"Edith,500,5\n" b"Frank,600,6\n"
    ),
}
text_files = {
    "nested/file1.txt": b"hello\n",
    "nested/file2": b"world",
    "nested/nested2/file1": b"hello\n",
    "nested/nested2/file2": b"world",
}
allfiles = dict(**files, **csv_files, **text_files)
a = TEST_BUCKET + "/tmp/test/a"
b = TEST_BUCKET + "/tmp/test/b"
c = TEST_BUCKET + "/tmp/test/c"
d = TEST_BUCKET + "/tmp/test/d"


@contextmanager
def gcs_maker(**kwargs):
    gcs = GCSFileSystem(TEST_PROJECT, token=GOOGLE_TOKEN, **kwargs)
    # invalidate cached state of gcs files
    gcs.invalidate_cache()
    try:
        try:
            # remove all the files that are in the bucket
            gcs.rm(TEST_BUCKET, recursive=True)
        except FileNotFoundError:
            pass
        try:
            # remove all the files that are in the bucket
            gcs.rm(TEST_BUCKET_2, recursive=True)
            # remove the bucket forr create/destroy tests
            # print('\n\n\n\n\nwe never gt herre')
            # gcs.rmdir(TEST_BUCKET_2)
        except FileNotFoundError:
            pass
        try:
            # remove the bucket forr create/destroy tests
            gcs.rmdir(TEST_BUCKET_2)
        except FileNotFoundError:
            pass
        try:
            gcs.mkdir(
                TEST_BUCKET,
                default_acl="authenticatedread",
                acl="authenticatedread",
            )
        except Exception:
            pass

        if RECORD_MODE == "all":
            gcs.pipe({TEST_BUCKET + "/" + k: v for k, v in allfiles.items()})

        # invalidate cached state of gcs files
        # without this, the local gcs object has no knowledge
        # of the above changes
        gcs.invalidate_cache()
        yield gcs
    finally:
        try:
            gcs.rm(gcs.find(TEST_BUCKET))
            pass
        except:  # noqa: E722
            pass
