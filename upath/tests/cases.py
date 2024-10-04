import os
import pickle
import re
import stat
import sys
import warnings
from pathlib import Path

import pytest
from fsspec import __version__ as fsspec_version
from fsspec import filesystem
from packaging.version import Version

from upath import UPath
from upath._stat import UPathStatResult


class BaseTests:
    SUPPORTS_EMPTY_DIRS = True

    path: UPath

    def test_cwd(self):
        with pytest.raises(NotImplementedError):
            self.path.cwd()

    def test_home(self):
        with pytest.raises(NotImplementedError):
            self.path.home()

    def test_stat(self):
        stat = self.path.stat()
        assert isinstance(stat, UPathStatResult)
        assert len(tuple(stat)) == os.stat_result.n_sequence_fields

        with warnings.catch_warnings():
            warnings.simplefilter("error")

            for idx in range(os.stat_result.n_sequence_fields):
                assert isinstance(stat[idx], int)
            for attr in UPathStatResult._fields + UPathStatResult._fields_extra:
                assert hasattr(stat, attr)

    def test_stat_dir_st_mode(self):
        base = self.path.stat()  # base folder
        assert stat.S_ISDIR(base.st_mode)

    def test_stat_file_st_mode(self):
        file1 = self.path.joinpath("file1.txt").stat()
        assert stat.S_ISREG(file1.st_mode)

    def test_stat_st_size(self):
        file1 = self.path.joinpath("file1.txt").stat()
        assert file1.st_size == 11

    def test_chmod(self):
        with pytest.raises(NotImplementedError):
            self.path.joinpath("file1.txt").chmod(777)

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

    def test_group(self):
        with pytest.raises(NotImplementedError):
            self.path.group()

    def test_is_dir(self):
        assert self.path.is_dir()

        path = self.path / "file1.txt"
        assert not path.is_dir()
        assert not (self.path / "not-existing-dir").is_dir()

    def test_is_file(self):
        path = self.path / "file1.txt"
        assert path.is_file()
        assert not self.path.is_file()

        assert not (self.path / "not-existing-file.txt").is_file()

    def test_is_absolute(self):
        assert self.path.is_absolute() is True

    def test_is_mount(self):
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
        assert next(self.path.parent.iterdir()).exists()

    def test_iterdir2(self, local_testdir):
        pl_path = Path(local_testdir) / "folder1"

        up_iter = list((self.path / "folder1").iterdir())
        pl_iter = list(pl_path.iterdir())

        for x in up_iter:
            assert x.exists()

        assert len(up_iter) == len(pl_iter)
        assert {p.name for p in pl_iter} == {u.name for u in up_iter}
        assert next(self.path.parent.iterdir()).exists()

    def test_iterdir_trailing_slash(self):
        files_noslash = list(self.path.joinpath("folder1").iterdir())
        files_slash = list(self.path.joinpath("folder1/").iterdir())
        assert files_noslash == files_slash

    def test_parents(self):
        p = self.path.joinpath("folder1", "file1.txt")
        assert p.is_file()
        assert p.parents[0] == p.parent
        assert p.parents[1] == p.parent.parent
        assert p.parents[0].name == "folder1"
        assert p.parents[1].name == self.path.name

    def test_lchmod(self):
        with pytest.raises(NotImplementedError):
            self.path.lchmod(mode=77)

    def test_lstat(self):
        with pytest.warns(UserWarning, match=r"[A-Za-z]+.stat"):
            st = self.path.lstat()
            assert st is not None

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

    @pytest.mark.skip(reason="_accessor is unsupported in universal_pathlib>0.1.4")
    def test_makedirs_exist_ok_true(self):
        new_dir = self.path.joinpath("parent", "child", "dir_may_not_exist")
        new_dir._accessor.makedirs(new_dir, exist_ok=True)
        if not self.SUPPORTS_EMPTY_DIRS:
            new_dir.joinpath(".file").touch()
        new_dir._accessor.makedirs(new_dir, exist_ok=True)

    @pytest.mark.skip(reason="_accessor is unsupported in universal_pathlib>0.1.4")
    def test_makedirs_exist_ok_false(self):
        new_dir = self.path.joinpath("parent", "child", "dir_may_exist")
        new_dir._accessor.makedirs(new_dir, exist_ok=False)
        if not self.SUPPORTS_EMPTY_DIRS:
            new_dir.joinpath(".file").touch()
        with pytest.raises(FileExistsError):
            new_dir._accessor.makedirs(new_dir, exist_ok=False)

    def test_open(self):
        p = self.path.joinpath("file1.txt")
        with p.open(mode="r") as f:
            assert f.read() == "hello world"
        with p.open(mode="rb") as f:
            assert f.read() == b"hello world"

    def test_open_buffering(self):
        p = self.path.joinpath("file1.txt")
        p.open(buffering=-1)

    def test_open_block_size(self):
        p = self.path.joinpath("file1.txt")
        with p.open(mode="r", block_size=8192) as f:
            assert f.read() == "hello world"

    def test_open_errors(self):
        p = self.path.joinpath("file1.txt")
        with p.open(mode="r", encoding="ascii", errors="strict") as f:
            assert f.read() == "hello world"

    def test_owner(self):
        with pytest.raises(NotImplementedError):
            self.path.owner()

    def test_read_bytes(self, pathlib_base):
        mock = self.path.joinpath("file2.txt")
        pl = pathlib_base.joinpath("file2.txt")
        assert mock.read_bytes() == pl.read_bytes()

    def test_read_text(self, local_testdir):
        upath = self.path.joinpath("file1.txt")
        assert (
            upath.read_text() == Path(local_testdir).joinpath("file1.txt").read_text()
        )

    def test_readlink(self):
        with pytest.raises(NotImplementedError):
            self.path.readlink()

    def test_rename(self):
        upath = self.path.joinpath("file1.txt")
        target = upath.parent.joinpath("file1_renamed.txt")
        moved = upath.rename(target)
        assert target == moved
        assert not upath.exists()
        assert moved.exists()
        # reverse with an absolute path as str
        back = moved.rename(str(upath))
        assert back == upath
        assert not moved.exists()
        assert back.exists()

    def test_rename2(self):
        upath = self.path.joinpath("folder1/file2.txt")
        target = "file2_renamed.txt"
        moved = upath.rename(target)
        target_path = upath.parent.joinpath(target).resolve()
        assert target_path == moved
        assert not upath.exists()
        assert moved.exists()
        # reverse with a relative path as UPath
        back = moved.rename(UPath("file2.txt"))
        assert back == upath
        assert not moved.exists()
        assert back.exists()

    def test_replace(self):
        pass

    def test_resolve(self):
        pass

    def test_rglob(self, pathlib_base):
        pattern = "*.txt"
        result = [*self.path.rglob(pattern)]
        expected = [*pathlib_base.rglob(pattern)]
        assert len(result) == len(expected)

    def test_symlink_to(self):
        pass

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

    def test_link_to(self):
        pass

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

    def test_fsspec_compat(self):
        fs = self.path.fs
        content = b"a,b,c\n1,2,3\n4,5,6"

        def strip_scheme(path):
            root = "" if sys.platform.startswith("win") else "/"
            return root + re.sub("^[a-z0-9]+:/*", "", str(path))

        upath1 = self.path / "output1.csv"
        p1 = strip_scheme(upath1)
        upath1.write_bytes(content)
        assert fs is upath1.fs
        with fs.open(p1) as f:
            assert f.read() == content
        upath1.unlink()

        # write with fsspec, read with upath
        upath2 = self.path / "output2.csv"
        p2 = strip_scheme(upath2)
        assert fs is upath2.fs
        with fs.open(p2, "wb") as f:
            f.write(content)
        assert upath2.read_bytes() == content
        upath2.unlink()

    def test_pickling(self):
        path = self.path
        pickled_path = pickle.dumps(path)
        recovered_path = pickle.loads(pickled_path)

        assert type(path) is type(recovered_path)
        assert str(path) == str(recovered_path)
        assert path.fs.storage_options == recovered_path.fs.storage_options

    def test_pickling_child_path(self):
        path = self.path / "subfolder" / "subsubfolder"
        pickled_path = pickle.dumps(path)
        recovered_path = pickle.loads(pickled_path)

        assert type(path) is type(recovered_path)
        assert str(path) == str(recovered_path)
        assert path.drive == recovered_path.drive
        assert path.root == recovered_path.root
        assert path.parts == recovered_path.parts
        assert path.fs.storage_options == recovered_path.fs.storage_options
        assert path.storage_options == recovered_path.storage_options

    def test_child_path(self):
        path_str = str(self.path).rstrip("/")
        path_a = UPath(f"{path_str}/folder")
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
        assert path.fs.storage_options == copy_path.fs.storage_options

    def test_with_name(self):
        path = self.path / "file.txt"
        path = path.with_name("file.zip")
        assert path.name == "file.zip"

    def test_with_suffix(self):
        path = self.path / "file.txt"
        path = path.with_suffix(".zip")
        assert path.suffix == ".zip"

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

    def test_private_url_attr_in_sync(self):
        p = self.path
        p1 = self.path.joinpath("c")
        p2 = self.path / "c"
        assert p1._url == p2._url
        assert p1._url != p._url
        assert p1.protocol == p2.protocol

    def test_as_uri(self):
        # test that we can reconstruct the path from the uri
        p0 = self.path
        uri = p0.as_uri()
        p1 = UPath(uri, **p0.fs.storage_options)
        assert p0 == p1

    def test_protocol(self):
        protocol = self.path.protocol
        protocols = [p] if isinstance((p := type(self.path.fs).protocol), str) else p
        print(protocol, protocols)
        assert protocol in protocols

    def test_storage_options(self):
        storage_options = self.path.storage_options
        assert storage_options == self.path.fs.storage_options

    def test_read_with_fsspec(self):
        p = self.path.joinpath("file2.txt")

        protocol = p.protocol
        storage_options = p.storage_options
        path = p.path

        fs = filesystem(protocol, **storage_options)
        with fs.open(path) as f:
            assert f.read() == b"hello world"

    @pytest.mark.xfail(
        sys.version_info >= (3, 13),
        reason="no support for private `._drv`, `._root`, `._parts` in 3.13",
    )
    def test_access_to_private_api(self):
        # DO NOT access these private attributes in your code
        p = UPath(str(self.path), **self.path.storage_options)
        assert isinstance(p._drv, str)
        p = UPath(str(self.path), **self.path.storage_options)
        assert isinstance(p._root, str)
        p = UPath(str(self.path), **self.path.storage_options)
        assert isinstance(p._parts, (list, tuple))

    def test_hashable(self):
        assert hash(self.path)

    def test_storage_options_dont_affect_hash(self):
        p0 = UPath(str(self.path), test_extra=1, **self.path.storage_options)
        p1 = UPath(str(self.path), test_extra=2, **self.path.storage_options)
        assert hash(p0) == hash(p1)

    def test_eq(self):
        p0 = UPath(str(self.path), test_extra=1, **self.path.storage_options)
        p1 = UPath(str(self.path), test_extra=1, **self.path.storage_options)
        p2 = UPath(str(self.path), test_extra=2, **self.path.storage_options)
        assert p0 == p1
        assert p0 != p2
        assert p1 != p2

    def test_samefile(self):
        f1 = self.path.joinpath("file1.txt")
        f2 = self.path.joinpath("file2.txt")

        assert f1.samefile(f2) is False
        assert f1.samefile(f2.path) is False
        assert f1.samefile(f1) is True
        assert f1.samefile(f1.path) is True
