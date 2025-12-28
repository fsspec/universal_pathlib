import pytest
from fsspec import get_filesystem_class

from upath import UnsupportedOperation
from upath import UPath
from upath.implementations.cloud import HfPath

from ..cases import JoinablePathTests
from ..cases import NonWritablePathTests
from ..cases import ReadablePathTests
from ..utils import OverrideMeta
from ..utils import overrides_base

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


class TestUPathHf(
    JoinablePathTests,
    ReadablePathTests,
    NonWritablePathTests,
    metaclass=OverrideMeta,
):
    @pytest.fixture(autouse=True, scope="function")
    def path(self, hf_fixture_with_readonly_mocked_hf_api):
        self.path = UPath(hf_fixture_with_readonly_mocked_hf_api)

    @overrides_base
    def test_is_correct_class(self):
        assert isinstance(self.path, HfPath)

    @overrides_base
    def test_iterdir_parent_iteration(self):
        # HfPath does not support listing all available Repositories
        with pytest.raises(UnsupportedOperation):
            super().test_iterdir_parent_iteration()
