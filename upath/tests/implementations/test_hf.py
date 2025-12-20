import pytest
from fsspec import get_filesystem_class

from upath import UPath
from upath.implementations.cloud import HfPath

from ..cases import BaseTests

try:
    get_filesystem_class("hf")
except ImportError:
    pytestmark = pytest.mark.skip


def test_hfpath():
    path = UPath("hf://HuggingFaceTB/SmolLM2-135M")
    assert isinstance(path, HfPath)
    try:
        assert path.exists()
    except AssertionError:
        from httpx import ConnectError
        from huggingface_hub import HfApi

        try:
            HfApi().repo_info("HuggingFaceTB/SmolLM2-135M")
        except ConnectError:
            pytest.xfail("No internet connection")
        except Exception as err:
            if "Service Unavailable" in str(err):
                pytest.xfail("HuggingFace API not reachable")
            raise


class TestUPathHf(BaseTests):
    @pytest.fixture(autouse=True, scope="function")
    def path(self, hf_fixture_with_readonly_mocked_hf_api):
        self.path = UPath(hf_fixture_with_readonly_mocked_hf_api)

    @pytest.mark.skip
    def test_mkdir(self):
        pass

    @pytest.mark.skip
    def test_mkdir_exists_ok_false(self):
        pass

    @pytest.mark.skip
    def test_mkdir_exists_ok_true(self):
        pass

    @pytest.mark.skip
    def test_mkdir_parents_true_exists_ok_true(self):
        pass

    @pytest.mark.skip
    def test_mkdir_parents_true_exists_ok_false(self):
        pass

    @pytest.mark.skip
    def test_makedirs_exist_ok_true(self):
        pass

    @pytest.mark.skip
    def test_makedirs_exist_ok_false(self):
        pass

    @pytest.mark.skip
    def test_touch(self):
        pass

    @pytest.mark.skip
    def test_touch_unlink(self):
        pass

    @pytest.mark.skip
    def test_write_bytes(self, pathlib_base):
        pass

    @pytest.mark.skip
    def test_write_text(self, pathlib_base):
        pass

    def test_fsspec_compat(self):
        pass

    def test_rename(self):
        pass

    def test_rename2(self):
        pass

    def test_move_local(self, tmp_path):
        pass

    def test_move_into_local(self, tmp_path):
        pass

    def test_move_memory(self, clear_fsspec_memory_cache):
        pass

    def test_move_into_memory(self, clear_fsspec_memory_cache):
        pass

    @pytest.mark.skip(reason="HfPath does not support listing repositories")
    def test_iterdir(self, local_testdir):
        pass

    @pytest.mark.skip(reason="HfPath does not support listing repositories")
    def test_iterdir2(self, local_testdir):
        pass

    @pytest.mark.skip(reason="HfPath does not currently test write")
    def test_rename_with_target_absolute(self, target_factory):
        return super().test_rename_with_target_absolute(target_factory)
