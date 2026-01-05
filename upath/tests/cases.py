import os
import pickle
import stat
import sys
import warnings
from pathlib import Path

import pytest
from fsspec import __version__ as fsspec_version
from fsspec import filesystem
from fsspec import get_filesystem_class
from packaging.version import Version
from pathlib_abc import PathParser
from pathlib_abc import vfspath

from upath import UnsupportedOperation
from upath import UPath
from upath._protocol import get_upath_protocol
from upath._stat import UPathStatResult
from upath.tests.utils import posixify
from upath.types import StatResultType


class JoinablePathTests:
    """Tests for JoinablePath interface.

    These tests verify pure path operations that don't require filesystem access:
    - Path parsing and components (parts, parents, name, stem, suffix, etc.)
    - Path manipulation (with_name, with_suffix, with_stem, joinpath, etc.)
    - Path comparison and hashing
    - Serialization (pickling)
    - URI handling
    """

    path: UPath

    def test_is_correct_class(self):
        raise NotImplementedError("must override")

    def test_parser(self):
        parser = self.path.parser
        assert isinstance(parser, PathParser)
        assert isinstance(parser.sep, str)
        assert parser.altsep is None or isinstance(parser.altsep, str)
        assert callable(parser.split)
        assert callable(parser.splitext)
        assert callable(parser.normcase)

    def test_with_segments(self):
        p = self.path.with_segments(self.path.__vfspath__(), "folder", "file.txt")
        assert p.parts[-2:] == ("folder", "file.txt")
        assert type(p) is type(self.path)

    def test___vfspath__(self):
        assert hasattr(self.path, "__vfspath__")
        assert callable(self.path.__vfspath__)
        str_path = vfspath(self.path)
        assert isinstance(str_path, str)

    def test_anchor(self):
        anchor = self.path.anchor
        assert isinstance(anchor, str)
        assert anchor == self.path.drive + self.path.root

    def test_is_absolute(self):
        assert self.path.is_absolute() is True

    def test_parents(self):
        p = self.path.joinpath("folder1", "file1.txt")
        assert p.parents[0] == p.parent
        assert p.parents[1] == p.parent.parent
        assert p.parents[0].name == "folder1"
        assert p.parents[1].name == self.path.name

    def test_with_name(self):
        path = self.path / "file.txt"
        path = path.with_name("file.zip")
        assert path.name == "file.zip"

    def test_with_suffix(self):
        path = self.path / "file.txt"
        path = path.with_suffix(".zip")
        assert path.suffix == ".zip"

    def test_suffix(self):
        path = self.path / "no_suffix"
        assert path.suffix == ""
        path = self.path / "file.txt"
        assert path.suffix == ".txt"
        path = self.path / "archive.tar.gz"
        assert path.suffix == ".gz"

    def test_suffixes(self):
        path = self.path / "no_suffix"
        assert path.suffixes == []
        path = self.path / "file.txt"
        assert path.suffixes == [".txt"]
        path = self.path / "archive.tar.gz"
        assert path.suffixes == [".tar", ".gz"]

    def test_with_stem(self):
        if sys.version_info < (3, 9):
            pytest.skip("with_stem only available on py3.9+")
        path = self.path / "file.txt"
        path = path.with_stem("document")
        assert path.stem == "document"

    def test_repr_after_with_name(self):
        p = self.path.joinpath("file.txt").with_name("file.zip")
        assert "file.zip" in repr(p)

    def test_repr_after_with_suffix(self):
        p = self.path.joinpath("file.txt").with_suffix(".zip")
        assert "file.zip" in repr(p)

    def test_child_path(self):
        path_str = self.path.__vfspath__()
        path_a = UPath(
            path_str, "folder", protocol=self.path.protocol, **self.path.storage_options
        )
        path_b = self.path / "folder"

        assert str(path_a) == str(path_b)
        assert path_a.root == path_b.root
        assert path_a.drive == path_b.drive

    def test_copy_path(self):
        path = self.path
        copy_path = UPath(path)

        assert type(path) is type(copy_path)
        assert str(path) == str(copy_path)
        assert path.drive == copy_path.drive
        assert path.root == copy_path.root
        assert path.parts == copy_path.parts
        assert path.storage_options == copy_path.storage_options

    def test_pickling(self):
        path = self.path
        pickled_path = pickle.dumps(path)
        recovered_path = pickle.loads(pickled_path)

        assert type(path) is type(recovered_path)
        assert str(path) == str(recovered_path)
        assert path.storage_options == recovered_path.storage_options

    def test_pickling_child_path(self):
        path = self.path / "subfolder" / "subsubfolder"
        pickled_path = pickle.dumps(path)
        recovered_path = pickle.loads(pickled_path)

        assert type(path) is type(recovered_path)
        assert str(path) == str(recovered_path)
        assert path.drive == recovered_path.drive
        assert path.root == recovered_path.root
        assert path.parts == recovered_path.parts
        assert path.storage_options == recovered_path.storage_options

    def test_as_uri(self):
        # test that we can reconstruct the path from the uri
        p0 = self.path
        uri = p0.as_uri()
        p1 = UPath(uri, **p0.storage_options)
        assert p0 == p1

    def test_protocol(self):
        protocol = self.path.protocol
        fs_cls = get_filesystem_class(protocol)
        protocols = [p] if isinstance((p := fs_cls.protocol), str) else p
        print(protocol, protocols)
        assert protocol in protocols

    def test_hashable(self):
        assert hash(self.path)

    def test_storage_options_dont_affect_hash(self):
        cls = type(self.path)
        p0 = cls(str(self.path), test_extra=1, **self.path.storage_options)
        p1 = cls(str(self.path), test_extra=2, **self.path.storage_options)
        assert hash(p0) == hash(p1)

    def test_eq(self):
        cls = type(self.path)
        p0 = cls(str(self.path), test_extra=1, **self.path.storage_options)
        p1 = cls(str(self.path), test_extra=1, **self.path.storage_options)
        p2 = cls(str(self.path), test_extra=2, **self.path.storage_options)
        assert p0 == p1
        assert p0 != p2
        assert p1 != p2

    def test_relative_to(self):
        base = self.path
        child = self.path / "folder1" / "file1.txt"
        relative = child.relative_to(base)
        assert str(relative) == "folder1/file1.txt"

    def test_is_relative_to(self):
        base = self.path
        child = self.path / "folder1" / "file1.txt"
        other = UPath("/some/other/path")

        assert child.is_relative_to(base) is True
        assert base.is_relative_to(child) is False
        assert child.is_relative_to(other) is False

    def test_full_match(self):
        p = self.path / "folder" / "file.txt"
        assert p.full_match("**/*") is True
        assert p.full_match("**/*.txt") is True
        assert p.full_match("*.doesnotexist") is False

    def test_trailing_slash_joinpath_is_identical(self):
        # setup
        cls = type(self.path)
        protocol = self.path.protocol
        path = self.path.path
        sopts = self.path.storage_options
        if not path:
            path = "something"
            path_with_slash = "something/"
        elif path.endswith("/"):
            path_with_slash = path
            path = path.removeprefix("/")
        else:
            path_with_slash = path + "/"
        key = "key/"

        # test
        a = cls(path_with_slash + key, protocol=protocol, **sopts)
        b = cls(path_with_slash, key, protocol=protocol, **sopts)
        c = cls(path_with_slash, protocol=protocol, **sopts).joinpath(key)
        d = cls(path_with_slash, protocol=protocol, **sopts) / key
        assert a.path == b.path == c.path == d.path

    def test_trailing_slash_is_stripped(self):
        has_meaningful_trailing_slash = getattr(
            self.path.parser, "has_meaningful_trailing_slash", False
        )
        if has_meaningful_trailing_slash:
            assert not self.path.joinpath("key").path.endswith("/")
            assert self.path.joinpath("key/").path.endswith("/")
        else:
            assert not self.path.joinpath("key").path.endswith("/")
            assert not self.path.joinpath("key/").path.endswith("/")

    def test_parents_are_absolute(self):
        # this is a cross implementation compatible way to ensure that
        # the path representing the root is absolute
        is_absolute = [p.is_absolute() for p in self.path.parents]
        assert all(is_absolute)

    def test_parents_end_at_anchor(self):
        p = self.path.joinpath("folder1", "file1.txt")
        assert p.parents[-1].path == posixify(p.anchor)

    def test_anchor_is_its_own_parent(self):
        p = self.path.joinpath("folder1", "file1.txt")
        p0 = p.parents[-1]
        assert p0.path == posixify(p.anchor)
        assert p0.parent.path == posixify(p.anchor)

    def test_private_url_attr_in_sync(self):
        p = self.path
        p1 = self.path.joinpath("c")
        p2 = self.path / "c"
        assert p1._url == p2._url
        assert p1._url != p._url
        assert p1.protocol == p2.protocol


class ReadablePathTests:
    """Tests for ReadablePath interface.

    These tests verify operations that read from the filesystem:
    - File/directory existence and type checks (exists, is_dir, is_file, etc.)
    - File metadata (stat, info)
    - Reading file contents (read_bytes, read_text, open for reading)
    - Directory listing (iterdir, glob, rglob)
    - Copy operations (read source)
    """

    path: UPath

    @pytest.fixture(autouse=True)
    def path_file(self, path):
        self.path_file = self.path.joinpath("file1.txt")

    def test_storage_options_match_fsspec(self):
        storage_options = self.path.storage_options
        assert storage_options == self.path.fs.storage_options

    def test_stat(self):
        stat_ = self.path.stat()

        # for debugging os.stat_result compatibility
        attrs = {attr for attr in dir(stat_) if attr.startswith("st_")}
        print(attrs)

        assert isinstance(stat_, StatResultType)
        assert len(tuple(stat_)) == os.stat_result.n_sequence_fields

        with warnings.catch_warnings():
            warnings.simplefilter("error")

            for idx in range(os.stat_result.n_sequence_fields):
                assert isinstance(stat_[idx], int)
            for attr in UPathStatResult._fields + UPathStatResult._fields_extra:
                assert hasattr(stat_, attr)

    def test_stat_dir_st_mode(self):
        base = self.path.stat()  # base folder
        assert stat.S_ISDIR(base.st_mode)

    def test_stat_file_st_mode(self):
        file1 = self.path_file.stat()
        assert stat.S_ISREG(file1.st_mode)

    def test_stat_st_size(self):
        file1 = self.path_file.stat()
        assert file1.st_size == 11

    @pytest.mark.parametrize(
        "url, expected", [("file1.txt", True), ("fakefile.txt", False)]
    )
    def test_exists(self, url, expected):
        path = self.path.joinpath(url)
        assert path.exists() == expected

    def test_expanduser(self):
        assert self.path.expanduser() == self.path

    @pytest.mark.parametrize(
        "pattern",
        (
            "*.txt",
            "*",
            pytest.param(
                "**/*.txt",
                marks=(
                    pytest.mark.xfail(reason="requires fsspec>=2023.9.0")
                    if Version(fsspec_version) < Version("2023.9.0")
                    else ()
                ),
            ),
        ),
    )
    def test_glob(self, pathlib_base, pattern):
        mock_glob = list(self.path.glob(pattern))
        path_glob = list(pathlib_base.glob(pattern))

        _mock_start = len(self.path.parts)
        mock_glob_normalized = sorted(
            [tuple(filter(None, a.parts[_mock_start:])) for a in mock_glob]
        )
        _path_start = len(pathlib_base.parts)
        path_glob_normalized = sorted([a.parts[_path_start:] for a in path_glob])

        print(mock_glob_normalized, path_glob_normalized)
        assert mock_glob_normalized == path_glob_normalized

    def test_is_dir(self):
        assert self.path.is_dir()

        path = self.path / "file1.txt"
        assert not path.is_dir()
        assert not (self.path / "not-existing-dir").is_dir()

    def test_is_file(self):
        path_exists = self.path / "file1.txt"
        assert path_exists.is_file()
        assert not (self.path / "not-existing-file.txt").is_file()

    def test_is_mount(self):
        try:
            self.path.is_mount()
        except UnsupportedOperation:
            pytest.skip(f"is_mount() not supported for {type(self.path).__name__}")
        else:
            assert self.path.is_mount() is False

    def test_is_symlink(self):
        assert self.path.is_symlink() is False

    def test_is_socket(self):
        assert self.path.is_socket() is False

    def test_is_fifo(self):
        assert self.path.is_fifo() is False

    def test_is_block_device(self):
        assert self.path.is_block_device() is False

    def test_is_char_device(self):
        assert self.path.is_char_device() is False

    def test_iterdir(self, local_testdir):
        pl_path = Path(local_testdir)

        up_iter = list(self.path.iterdir())
        pl_iter = list(pl_path.iterdir())

        for x in up_iter:
            assert x.name != ""
            assert x.exists()

        assert len(up_iter) == len(pl_iter)
        assert {p.name for p in pl_iter} == {u.name for u in up_iter}

    def test_iterdir_parent_iteration(self):
        assert next(self.path.parent.iterdir()).exists()

    def test_iterdir2(self, local_testdir):
        pl_path = Path(local_testdir) / "folder1"

        up_iter = list((self.path / "folder1").iterdir())
        pl_iter = list(pl_path.iterdir())

        for x in up_iter:
            assert x.exists()

        assert len(up_iter) == len(pl_iter)
        assert {p.name for p in pl_iter} == {u.name for u in up_iter}

    def test_iterdir_trailing_slash(self):
        files_noslash = list(self.path.joinpath("folder1").iterdir())
        files_slash = list(self.path.joinpath("folder1/").iterdir())
        assert files_noslash == files_slash

    def test_lstat(self):
        with pytest.warns(UserWarning, match=r"[A-Za-z]+.stat"):
            st = self.path.lstat()
            assert st is not None

    def test_cwd(self):
        with pytest.raises(UnsupportedOperation):
            self.path.cwd()

    def test_home(self):
        with pytest.raises(UnsupportedOperation):
            self.path.home()

    def test_open(self):
        p = self.path_file
        with p.open(mode="r") as f:
            assert f.read() == "hello world"
        with p.open(mode="rb") as f:
            assert f.read() == b"hello world"

    def test_open_buffering(self):
        p = self.path_file
        p.open(buffering=-1)

    def test_open_block_size(self):
        p = self.path_file
        with p.open(mode="r", block_size=8192) as f:
            assert f.read() == "hello world"

    def test_open_errors(self):
        p = self.path_file
        with p.open(mode="r", encoding="ascii", errors="strict") as f:
            assert f.read() == "hello world"

    def test_read_bytes(self):
        mock = self.path.joinpath("file2.txt")
        assert mock.read_bytes() == b"hello world"

    def test_read_text(self):
        upath = self.path.joinpath("file1.txt")
        assert upath.read_text() == "hello world"

    def test_read_text_encoding(self):
        upath = self.path_file
        content = upath.read_text(encoding="utf-8")
        assert content == "hello world"

    def test_read_text_errors(self):
        upath = self.path_file
        content = upath.read_text(encoding="ascii", errors="strict")
        assert content == "hello world"

    def test_rglob(self, pathlib_base):
        pattern = "*.txt"
        result = [*self.path.rglob(pattern)]
        expected = [*pathlib_base.rglob(pattern)]
        assert len(result) == len(expected)

    def test_walk(self, local_testdir):
        def _raise(x):
            raise x

        # collect walk results from UPath
        upath_walk = []
        for dirpath, dirnames, filenames in self.path.walk(on_error=_raise):
            rel_dirpath = dirpath.relative_to(self.path)
            upath_walk.append((str(rel_dirpath), sorted(dirnames), sorted(filenames)))
        upath_walk.sort()

        # collect walk results using os.walk (compatible with Python 3.9+)
        os_walk = []
        for dirpath, dirnames, filenames in os.walk(local_testdir):
            rel_dirpath = os.path.relpath(dirpath, local_testdir)
            os_walk.append((rel_dirpath, sorted(dirnames), sorted(filenames)))
        os_walk.sort()

        assert upath_walk == os_walk

    def test_walk_top_down_false(self):
        def _raise(x):
            raise x

        # test walk with top_down=False returns directories after their contents
        paths_seen = []
        for dirpath, _, _ in self.path.walk(top_down=False, on_error=_raise):
            paths_seen.append(dirpath)

        # in bottom-up walk, parent directories should come after children
        for i, path in enumerate(paths_seen):
            for _, other in enumerate(paths_seen[i + 1 :], start=i + 1):
                # if path is a parent of other, path should come after other
                if other.is_relative_to(path) and other != path:
                    pytest.fail(f"In bottom-up walk, {path} should come after {other}")

    def test_samefile(self):
        f1 = self.path.joinpath("file1.txt")
        f2 = self.path.joinpath("file2.txt")

        assert f1.samefile(f2) is False
        assert f1.samefile(f2.path) is False
        assert f1.samefile(f1) is True
        assert f1.samefile(f1.path) is True

    def test_info(self):
        p0 = self.path.joinpath("file1.txt")
        p1 = self.path.joinpath("folder1")

        assert p0.info.exists() is True
        assert p0.info.is_file() is True
        assert p0.info.is_dir() is False
        assert p0.info.is_symlink() is False
        assert p1.info.exists() is True
        assert p1.info.is_file() is False
        assert p1.info.is_dir() is True
        assert p1.info.is_symlink() is False

    def test_copy_local(self, tmp_path: Path):
        target = UPath(tmp_path) / "target-file1.txt"

        source = self.path_file
        content = source.read_text()
        source.copy(target)
        assert target.exists()
        assert target.read_text() == content

    @pytest.mark.parametrize("target_type", [str, Path, UPath])
    def test_copy_into__file_to_str_tempdir(self, tmp_path: Path, target_type):
        tmp_path = tmp_path.joinpath("somewhere")
        tmp_path.mkdir()
        target_dir = target_type(tmp_path)
        assert isinstance(target_dir, target_type)

        source = self.path_file
        source.copy_into(target_dir)
        target = tmp_path.joinpath(source.name)

        assert target.exists()
        assert target.read_text() == source.read_text()

    @pytest.mark.parametrize("target_type", [str, Path, UPath])
    def test_copy_into__dir_to_str_tempdir(self, tmp_path: Path, target_type):
        tmp_path = tmp_path.joinpath("somewhere")
        tmp_path.mkdir()
        target_dir = target_type(tmp_path)
        assert isinstance(target_dir, target_type)

        source_dir = self.path.joinpath("folder1")
        assert source_dir.is_dir()
        source_dir.copy_into(target_dir)
        target = tmp_path.joinpath(source_dir.name)

        assert target.exists()
        assert target.is_dir()
        for item in source_dir.iterdir():
            target_item = target.joinpath(item.name)
            assert target_item.exists()
            if item.is_file():
                assert target_item.read_text() == item.read_text()

    def test_copy_into_local(self, tmp_path: Path):
        target_dir = UPath(tmp_path) / "target-dir"
        target_dir.mkdir()

        source = self.path_file
        content = source.read_text()
        source.copy_into(target_dir)
        target = target_dir / source.name
        assert target.exists()
        assert target.read_text() == content

    def test_copy_memory(self, clear_fsspec_memory_cache):
        target = UPath("memory:///target-file1.txt")
        source = self.path_file
        content = source.read_text()
        source.copy(target)
        assert target.exists()
        assert target.read_text() == content

    def test_copy_into_memory(self, clear_fsspec_memory_cache):
        target_dir = UPath("memory:///target-dir")
        target_dir.mkdir()

        source = self.path_file
        content = source.read_text()
        source.copy_into(target_dir)
        target = target_dir / source.name
        assert target.exists()
        assert target.read_text() == content

    def test_copy_exceptions(self, tmp_path: Path):
        source = self.path_file
        # target is a directory
        target = UPath(tmp_path) / "target-folder"
        target.mkdir()
        # FIXME: pytest.raises(IsADirectoryError) not working on Windows
        with pytest.raises(OSError):
            source.copy(target)
        # target parent does not exist
        target = UPath(tmp_path) / "nonexistent-dir" / "target-file1.txt"
        with pytest.raises(FileNotFoundError):
            source.copy(target)

    def test_copy_into_exceptions(self, tmp_path: Path):
        source = self.path_file
        # target is not a directory
        target_file = UPath(tmp_path) / "target-file.txt"
        target_file.write_text("content")
        # FIXME: pytest.raises(NotADirectoryError) not working on Windows
        with pytest.raises(OSError):
            source.copy_into(target_file)
        # target dir does not exist
        target_dir = UPath(tmp_path) / "nonexistent-dir"
        with pytest.raises(FileNotFoundError):
            source.copy_into(target_dir)

    def test_read_with_fsspec(self):
        p = self.path_file

        protocol = p.protocol
        storage_options = p.storage_options
        path = p.path

        fs = filesystem(protocol, **storage_options)
        with fs.open(path) as f:
            assert f.read() == b"hello world"

    def test_readlink(self):
        with pytest.raises(UnsupportedOperation):
            self.path.readlink()

    def test_group(self):
        with pytest.raises(UnsupportedOperation):
            self.path.group()

    def test_owner(self):
        with pytest.raises(UnsupportedOperation):
            self.path.owner()


# =============================================================================
# WritablePathTests: Tests for writable path operations
# =============================================================================


class _CommonWritablePathTests:

    SUPPORTS_EMPTY_DIRS = True

    path: UPath

    def test_chmod(self):
        with pytest.raises(NotImplementedError):
            self.path_file.chmod(777)

    def test_lchmod(self):
        with pytest.raises(UnsupportedOperation):
            self.path.lchmod(mode=0o777)

    def test_symlink_to(self):
        with pytest.raises(UnsupportedOperation):
            self.path_file.symlink_to("target")
        with pytest.raises(UnsupportedOperation):
            self.path.joinpath("link").symlink_to("target")

    def test_hardlink_to(self):
        with pytest.raises(UnsupportedOperation):
            self.path_file.symlink_to("target")
        with pytest.raises(UnsupportedOperation):
            self.path.joinpath("link").hardlink_to("target")


class NonWritablePathTests(_CommonWritablePathTests):

    def test_mkdir_raises(self):
        with pytest.raises(UnsupportedOperation):
            self.path.mkdir()

    def test_touch_raises(self):
        with pytest.raises(UnsupportedOperation):
            self.path.touch()

    def test_unlink(self):
        with pytest.raises(UnsupportedOperation):
            self.path.unlink()

    def test_write_bytes(self):
        with pytest.raises(UnsupportedOperation):
            self.path_file.write_bytes(b"abc")

    def test_write_text(self):
        with pytest.raises(UnsupportedOperation):
            self.path_file.write_text("abc")


class WritablePathTests(_CommonWritablePathTests):
    """Tests for WritablePath interface.

    These tests verify operations that write to the filesystem:
    - Creating directories (mkdir)
    - Creating files (touch)
    - Writing file contents (write_bytes, write_text)
    - Removing files/directories (unlink, rmdir)
    """

    def test_mkdir(self):
        new_dir = self.path.joinpath("new_dir")
        new_dir.mkdir()
        if not self.SUPPORTS_EMPTY_DIRS:
            new_dir.joinpath(".file").touch()
        assert new_dir.exists()

    def test_mkdir_exists_ok_true(self):
        new_dir = self.path.joinpath("new_dir_may_exists")
        new_dir.mkdir()
        if not self.SUPPORTS_EMPTY_DIRS:
            new_dir.joinpath(".file").touch()
        new_dir.mkdir(exist_ok=True)

    def test_mkdir_exists_ok_false(self):
        new_dir = self.path.joinpath("new_dir_may_not_exists")
        new_dir.mkdir()
        if not self.SUPPORTS_EMPTY_DIRS:
            new_dir.joinpath(".file").touch()
        with pytest.raises(FileExistsError):
            new_dir.mkdir(exist_ok=False)

    def test_mkdir_parents_true_exists_ok_true(self):
        new_dir = self.path.joinpath("parent", "new_dir_may_not_exist")
        new_dir.mkdir(parents=True)
        if not self.SUPPORTS_EMPTY_DIRS:
            new_dir.joinpath(".file").touch()
        new_dir.mkdir(parents=True, exist_ok=True)

    def test_mkdir_parents_true_exists_ok_false(self):
        new_dir = self.path.joinpath("parent", "new_dir_may_exist")
        new_dir.mkdir(parents=True)
        if not self.SUPPORTS_EMPTY_DIRS:
            new_dir.joinpath(".file").touch()
        with pytest.raises(FileExistsError):
            new_dir.mkdir(parents=True, exist_ok=False)

    def test_touch_exists_ok_false(self):
        f = self.path.joinpath("file1.txt")
        assert f.exists()
        with pytest.raises(FileExistsError):
            f.touch(exist_ok=False)

    def test_touch_exists_ok_true(self):
        f = self.path.joinpath("file1.txt")
        assert f.exists()
        data = f.read_text()
        f.touch(exist_ok=True)
        assert f.read_text() == data

    def test_touch(self):
        path = self.path.joinpath("test_touch.txt")
        assert not path.exists()
        path.touch()
        assert path.exists()

    def test_touch_unlink(self):
        path = self.path.joinpath("test_touch.txt")
        path.touch()
        assert path.exists()
        path.unlink()
        assert not path.exists()

        # should raise FileNotFoundError since file is missing
        with pytest.raises(FileNotFoundError):
            path.unlink()

        # file doesn't exists, but missing_ok is True
        path.unlink(missing_ok=True)

    def test_write_bytes(self, pathlib_base):
        fn = "test_write_bytes.txt"
        s = b"hello_world"
        path = self.path.joinpath(fn)
        path.write_bytes(s)
        assert path.read_bytes() == s

    def test_write_text(self, pathlib_base):
        fn = "test_write_text.txt"
        s = "hello_world"
        path = self.path.joinpath(fn)
        path.write_text(s)
        assert path.read_text() == s

    def test_write_text_encoding(self):
        fn = "test_write_text_enc.txt"
        s = "hello_world"
        path = self.path.joinpath(fn)
        path.write_text(s, encoding="utf-8")
        assert path.read_text(encoding="utf-8") == s

    def test_write_text_errors(self):
        fn = "test_write_text_errors.txt"
        s = "hello_world"
        path = self.path.joinpath(fn)
        path.write_text(s, encoding="ascii", errors="strict")
        assert path.read_text(encoding="ascii") == s


class ReadWritePathTests:
    """Tests requiring both ReadablePath and WritablePath interfaces.

    These tests verify operations that need both read and write access:
    - Rename/move operations
    - File system setup/teardown
    - Operations that verify write results by reading
    - rmdir operations
    """

    SUPPORTS_EMPTY_DIRS = True

    path: UPath

    def test_rename(self):
        p_source = self.path.joinpath("file1.txt")
        p_target = self.path.joinpath("file1_renamed.txt")

        p_moved = p_source.rename(p_target)
        assert p_target == p_moved
        assert not p_source.exists()
        assert p_moved.exists()

        p_revert = p_moved.rename(p_source)
        assert p_revert == p_source
        assert not p_moved.exists()
        assert p_revert.exists()

    @pytest.fixture
    def supports_cwd(self):
        # intentionally called on the instance to support ProxyUPath().cwd()
        try:
            self.path.cwd()
        except UnsupportedOperation:
            return False
        else:
            return True

    @pytest.mark.parametrize(
        "target_factory",
        [
            lambda obj, name: name,
            lambda obj, name: UPath(name),
            lambda obj, name: Path(name),
            lambda obj, name: obj.joinpath(name).relative_to(obj),
        ],
        ids=[
            "str_relative",
            "plain_upath_relative",
            "plain_path_relative",
            "self_upath_relative",
        ],
    )
    def test_rename_with_target_relative(
        self, request, monkeypatch, supports_cwd, target_factory, tmp_path
    ):
        source = self.path.joinpath("folder1/file2.txt")
        target = target_factory(self.path, "file2_renamed.txt")

        source_text = source.read_text()
        if supports_cwd:
            cid = request.node.callspec.id
            cwd = tmp_path.joinpath(cid)
            cwd.mkdir(parents=True, exist_ok=True)
            monkeypatch.chdir(cwd)

            t = source.rename(target)
            assert (t.protocol == UPath(target).protocol) or UPath(
                target
            ).protocol == ""
            assert (t.path == UPath(target).path) or (
                t.path == UPath(target).absolute().path
            )
            assert t.exists()
            assert t.read_text() == source_text

        else:
            with pytest.raises(UnsupportedOperation):
                source.rename(target)

    @pytest.mark.parametrize(
        "target_factory",
        [
            lambda obj, name: obj.joinpath(name).absolute().as_posix(),
            lambda obj, name: UPath(obj.absolute().joinpath(name).path),
            lambda obj, name: Path(obj.absolute().joinpath(name).path),
            lambda obj, name: obj.absolute().joinpath(name),
        ],
        ids=[
            "str_absolute",
            "plain_upath_absolute",
            "plain_path_absolute",
            "self_upath_absolute",
        ],
    )
    def test_rename_with_target_absolute(self, target_factory):
        from upath._chain import Chain
        from upath._chain import FSSpecChainParser

        source = self.path.joinpath("folder1/file2.txt")
        target = target_factory(self.path, "file2_renamed.txt")

        source_text = source.read_text()
        t = source.rename(target)
        assert get_upath_protocol(target) in {t.protocol, ""}
        assert t.path == Chain.from_list(
            FSSpecChainParser().unchain(str(target))
        ).active_path.replace("\\", "/")
        assert t.exists()
        assert t.read_text() == source_text

    def test_replace(self):
        pass

    def test_resolve(self):
        pass

    def test_rmdir_no_dir(self):
        p = self.path.joinpath("file1.txt")
        with pytest.raises(NotADirectoryError):
            p.rmdir()

    def test_iterdir_no_dir(self):
        p = self.path.joinpath("file1.txt")
        assert p.is_file()
        with pytest.raises(NotADirectoryError):
            _ = list(p.iterdir())

    def test_rmdir_not_empty(self):
        p = self.path.joinpath("folder1")
        with pytest.raises(OSError, match="not empty"):
            p.rmdir(recursive=False)

    def test_fsspec_compat(self):
        fs = self.path.fs
        content = b"a,b,c\n1,2,3\n4,5,6"

        upath1 = self.path / "output1.csv"
        p1 = upath1.path
        upath1.write_bytes(content)
        assert fs._fs_token == upath1.fs._fs_token
        if fs.cachable:  # codespell:ignore cachable
            assert fs is upath1.fs
        with fs.open(p1) as f:
            assert f.read() == content
        upath1.unlink()

        # write with fsspec, read with upath
        upath2 = self.path / "output2.csv"
        p2 = upath2.path
        if fs.cachable:  # codespell:ignore cachable
            assert fs is upath2.fs
        with fs.open(p2, "wb") as f:
            f.write(content)
        assert upath2.read_bytes() == content
        upath2.unlink()

    def test_move_local(self, tmp_path: Path):
        target = UPath(tmp_path) / "target-file1.txt"

        source = self.path / "file1.txt"
        content = source.read_text()
        source.move(target)
        assert target.exists()
        assert target.read_text() == content
        assert not source.exists()

    def test_move_into_local(self, tmp_path: Path):
        target_dir = UPath(tmp_path) / "target-dir"
        target_dir.mkdir()

        source = self.path / "file1.txt"
        content = source.read_text()
        source.move_into(target_dir)
        target = target_dir / "file1.txt"
        assert target.exists()
        assert target.read_text() == content
        assert not source.exists()

    def test_move_memory(self, clear_fsspec_memory_cache):
        target = UPath("memory:///target-file1.txt")
        source = self.path / "file1.txt"
        content = source.read_text()
        source.move(target)
        assert target.exists()
        assert target.read_text() == content
        assert not source.exists()

    def test_move_into_memory(self, clear_fsspec_memory_cache):
        target_dir = UPath("memory:///target-dir")
        target_dir.mkdir()

        source = self.path / "file1.txt"
        content = source.read_text()
        source.move_into(target_dir)
        target = target_dir / "file1.txt"
        assert target.exists()
        assert target.read_text() == content
        assert not source.exists()

    def prepare_file_system(self):
        self.make_top_folder()
        self.make_test_files()

    def make_top_folder(self):
        self.path.mkdir(parents=True, exist_ok=True)

    def make_test_files(self):
        folder1 = self.path.joinpath("folder1")
        folder1.mkdir(exist_ok=True)
        folder1_files = ["file1.txt", "file2.txt"]
        for f in folder1_files:
            p = folder1.joinpath(f)
            p.touch()
            p.write_text(f)

        file1 = self.path.joinpath("file1.txt")
        file1.touch()
        file1.write_text("hello world")
        file2 = self.path.joinpath("file2.txt")
        file2.touch()
        file2.write_bytes(b"hello world")


class BaseTests(
    JoinablePathTests,
    ReadablePathTests,
    WritablePathTests,
    ReadWritePathTests,
):
    """Comprehensive test suite combining all path operation tests.

    This class composes all the individual test suites for testing UPath
    implementations that support full read/write functionality. For UPath
    subclasses with limited functionality (e.g., read-only), use the
    appropriate subset of test classes:

    - JoinablePathTests: Pure path operations (no I/O)
    - ReadablePathTests: Read-only operations
    - WritablePathTests: Write-only operations
    - ReadWritePathTests: Operations requiring both read and write

    Example usage for a read-only UPath:

        class TestMyReadOnlyPath(JoinablePathTests, ReadablePathTests):
            @pytest.fixture(autouse=True)
            def setup(self, ...):
                self.path = MyReadOnlyUPath(...)
    """

    SUPPORTS_EMPTY_DIRS = True

    path: UPath
