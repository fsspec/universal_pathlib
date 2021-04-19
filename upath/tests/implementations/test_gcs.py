import pytest
import os
from contextlib import contextmanager

from upath import UPath
from upath.implementations.gcs import GCSPath
from upath.tests.test_core import TestUpath

from gcsfs import GCSFileSystem


TEST_PROJECT = os.environ.get("GCSFS_TEST_PROJECT", "test_project")
TEST_BUCKET = os.environ.get("GCSFS_TEST_BUCKET", "gcsfs-testing")
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
RECORD_MODE = os.environ.get("GCSFS_RECORD_MODE", "none")


@contextmanager
def gcs_maker(populate=False, **kwargs):
    gcs = GCSFileSystem(TEST_PROJECT, token=GOOGLE_TOKEN, **kwargs)
    gcs.invalidate_cache()
    try:
        # ensure we're empty.
        try:
            gcs.rm(TEST_BUCKET, recursive=True)
        except FileNotFoundError:
            pass
        try:
            gcs.mkdir(
                TEST_BUCKET,
                default_acl="authenticatedread",
                acl="publicReadWrite",
            )
        except Exception:
            pass

        # if populate:
        #     gcs.pipe({TEST_BUCKET + "/" + k: v for k, v in allfiles.items()})
        gcs.invalidate_cache()
        yield gcs
    finally:
        try:
            gcs.rm(gcs.find(TEST_BUCKET))
        except:  # noqa: E722
            pass


@pytest.fixture(scope="class")
def gcsfs():
    with gcs_maker() as gcs:
        yield gcs


class TestGCSPath(TestUpath):
    @pytest.fixture(autouse=True)
    def path(self, local_testdir, gcsfs):
        path = f"gcs:/{local_testdir}"
        self.path = UPath(path, TEST_PROJECT, token=GOOGLE_TOKEN)
        self.prepare_file_system()

    def test_is_GCSPath(self):
        assert isinstance(self.path, GCSPath)
