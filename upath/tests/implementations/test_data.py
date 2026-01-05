import stat

import pytest

from upath import UnsupportedOperation
from upath import UPath
from upath.implementations.data import DataPath

from ..cases import JoinablePathTests
from ..cases import NonWritablePathTests
from ..cases import ReadablePathTests
from ..utils import OverrideMeta
from ..utils import overrides_base


class TestUPathDataPath(
    JoinablePathTests,
    ReadablePathTests,
    NonWritablePathTests,
    metaclass=OverrideMeta,
):
    """
    Unit-tests for the DataPath implementation of UPath.
    """

    @pytest.fixture(autouse=True)
    def path(self):
        path = "data:text/plain;base64,aGVsbG8gd29ybGQ="
        self.path = UPath(path)

    @pytest.fixture(autouse=True)
    def path_file(self, path):
        self.path_file = self.path

    @overrides_base
    def test_is_correct_class(self):
        assert isinstance(self.path, DataPath)

    @overrides_base
    def test_with_segments(self):
        # DataPath does not support joins, so in all usual cases it'll raise
        with pytest.raises(UnsupportedOperation):
            self.path.with_segments("data:text/plain;base64,", "aGVsbG8K")
        # but you can instantiate with a single full url
        self.path.with_segments("data:text/plain;base64,aGVsbG8K")

    @overrides_base
    def test_parents(self):
        # DataPath is always a absolute path with no parents
        assert self.path.parents == []

    @overrides_base
    def test_with_name(self):
        # DataPath does not support name changes
        with pytest.raises(UnsupportedOperation):
            self.path.with_name("newname")

    @overrides_base
    def test_with_suffix(self):
        # DataPath does not support suffix changes
        with pytest.raises(UnsupportedOperation):
            self.path.with_suffix(".new")

    @overrides_base
    def test_with_stem(self):
        # DataPath does not support stem changes
        with pytest.raises(UnsupportedOperation):
            self.path.with_stem("newname")

    @overrides_base
    def test_suffix(self):
        # DataPath does not have suffixes
        assert self.path.suffix == ""

    @overrides_base
    def test_suffixes(self):
        # DataPath does not have suffixes
        assert self.path.suffixes == []

    @overrides_base
    def test_repr_after_with_name(self):
        with pytest.raises(UnsupportedOperation):
            repr(self.path.with_name("data:,ABC"))

    @overrides_base
    def test_repr_after_with_suffix(self):
        with pytest.raises(UnsupportedOperation):
            repr(self.path.with_suffix(""))

    @overrides_base
    def test_child_path(self):
        # DataPath does not support joins, so child paths are unsupported
        with pytest.raises(UnsupportedOperation):
            super().test_child_path()

    @overrides_base
    def test_pickling_child_path(self):
        # DataPath does not support joins, so child paths are unsupported
        with pytest.raises(UnsupportedOperation):
            super().test_pickling_child_path()

    @overrides_base
    def test_relative_to(self):
        # DataPath only relative_to with itself
        with pytest.raises(ValueError):
            self.path.relative_to("data:,ABC")
        self.path.relative_to(self.path)

    @overrides_base
    def test_is_relative_to(self):
        # DataPath only relative_to with itself
        assert not self.path.is_relative_to("data:,ABC")
        assert self.path.is_relative_to(self.path)

    @overrides_base
    def test_full_match(self):
        assert self.path.full_match("*")
        assert not self.path.full_match("xxx")

    @overrides_base
    def test_trailing_slash_joinpath_is_identical(self):
        # DataPath has no slashes, and is not joinable
        with pytest.raises(UnsupportedOperation):
            super().test_trailing_slash_joinpath_is_identical()

    @overrides_base
    def test_trailing_slash_is_stripped(self):
        # DataPath has no slashes, and is not joinable
        with pytest.raises(UnsupportedOperation):
            super().test_trailing_slash_is_stripped()

    @overrides_base
    def test_parents_end_at_anchor(self):
        # DataPath does not support joins
        with pytest.raises(UnsupportedOperation):
            super().test_parents_end_at_anchor()

    @overrides_base
    def test_anchor_is_its_own_parent(self):
        # DataPath does not support joins
        assert self.path.path == self.path.parent.path

    @overrides_base
    def test_private_url_attr_in_sync(self):
        # DataPath does not support joins, so we check on self.path
        assert self.path._url

    @overrides_base
    def test_stat_dir_st_mode(self):
        # DataPath does not have directories
        assert not stat.S_ISDIR(self.path.stat().st_mode)

    @overrides_base
    def test_exists(self):
        # A valid DataPath always exists
        assert self.path.exists()

    @overrides_base
    def test_glob(self):
        # DataPath does not have dirs, joins or globs
        assert list(self.path.glob("*")) == []

    @overrides_base
    def test_rglob(self):
        # DataPath does not have dirs, joins or globs
        assert list(self.path.rglob("*")) == []

    @overrides_base
    def test_is_dir(self):
        # DataPath does not have directories
        assert not self.path.is_dir()

    @overrides_base
    def test_is_file(self):
        # DataPath is always a file
        assert self.path.is_file()

    @overrides_base
    def test_iterdir(self):
        # DataPath does not have directories
        with pytest.raises(NotADirectoryError):
            self.path.iterdir()

    @overrides_base
    def test_iterdir_parent_iteration(self):
        with pytest.raises(NotADirectoryError):
            super().test_iterdir_parent_iteration()

    @overrides_base
    def test_iterdir2(self):
        # DataPath does not have directories, or joins
        with pytest.raises(NotADirectoryError):
            self.path_file.iterdir()

    @overrides_base
    def test_iterdir_trailing_slash(self):
        # DataPath does not have directories, or joins
        with pytest.raises(UnsupportedOperation):
            super().test_iterdir_trailing_slash()

    @overrides_base
    def test_read_bytes(self):
        assert self.path.read_bytes() == b"hello world"

    @overrides_base
    def test_read_text(self):
        assert self.path.read_text() == "hello world"

    @overrides_base
    def test_walk(self):
        # DataPath does not have directories
        assert list(self.path.walk()) == []

    @overrides_base
    def test_walk_top_down_false(self):
        # DataPath does not have directories
        assert list(self.path.walk(top_down=False)) == []

    @overrides_base
    def test_samefile(self):
        # DataPath doesn't have joins, so only identical paths are samefile
        f1 = UPath("data:text/plain;base64,aGVsbG8gd29ybGQ=")
        f2 = UPath("data:text/plain;base64,SGVsbG8gd29ybGQ=")

        assert f1.samefile(f2) is False
        assert f1.samefile(f2.path) is False
        assert f1.samefile(f1) is True
        assert f1.samefile(f1.path) is True

    @overrides_base
    def test_info(self):
        # DataPath info checks
        p0 = self.path

        assert p0.info.exists() is True
        assert p0.info.is_file() is True
        assert p0.info.is_dir() is False
        assert p0.info.is_symlink() is False

    @overrides_base
    def test_mkdir_raises(self):
        # DataPaths always exist and are files
        with pytest.raises(FileExistsError):
            self.path_file.mkdir()

    @overrides_base
    def test_touch_raises(self):
        # DataPaths always exist, so touch is a noop
        self.path_file.touch()

    @overrides_base
    def test_unlink(self):
        # DataPaths can't be deleted
        with pytest.raises(UnsupportedOperation):
            self.path_file.unlink()

    @overrides_base
    def test_copy_into__dir_to_str_tempdir(self):
        # There are no directories in DataPath
        assert not self.path.is_dir()
