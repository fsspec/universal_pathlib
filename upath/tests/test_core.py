import pathlib
from pathlib import Path

import pytest

from upath import UPath
from upath.errors import NotDirectoryError

@pytest.fixture()
def pathlib_base(local_testdir):
    return Path(local_testdir)


def test_posix_path(local_testdir):
    assert isinstance(UPath(local_testdir), pathlib.PosixPath)


class TestUpath:

    @pytest.fixture(autouse=True)
    def path(self, local_testdir):
        self.path = UPath(f'mock:{local_testdir}')
        print(self.path)


    def test_cwd(self):
        print('test_cwd')
        with pytest.raises(NotImplementedError):
            self.path.cwd()
        
    def test_home(self):
        with pytest.raises(NotImplementedError):
            self.path.home()


    def test_stat(self):
        stat = self.path.stat()
        print(stat)
        assert stat

        
    def test_chmod(self):
        with pytest.raises(NotImplementedError):
            self.path.joinpath('file1.txt').chmod(777)

    @pytest.mark.parametrize('url, expected', [('file1.txt', True), ('fakefile.txt', False)])
    def test_exists(self, url, expected):
        path = self.path.joinpath(url)
        assert path.exists() == expected

    def test_expanduser(self):
        with pytest.raises(NotImplementedError):
            self.path.expanduser()

    def test_glob(self, pathlib_base):
        mock_glob = list(self.path.glob('**.txt'))
        path_glob = list(pathlib_base.glob('**/*.txt'))

        assert len(mock_glob) == len(path_glob)
        assert all(map(lambda m: m.path in [str(p) for p in path_glob], mock_glob))

    def test_group(self):
        with pytest.raises(NotImplementedError):
            self.path.group()

    def test_is_dir(self):
        assert self.path.is_dir()

        path = self.path.joinpath('file1.txt')
        assert not path.is_dir()

    def test_is_file(self):
        path = self.path.joinpath('file1.txt')
        assert path.is_file()
        assert not self.path.is_file()

    def test_is_mount(self):
        with pytest.raises(NotImplementedError):
            self.path.is_mount()

    def test_is_symlink(self):
        with pytest.raises(NotImplementedError):
            self.path.is_symlink()

    def test_is_socket(self):
        with pytest.raises(NotImplementedError):
            self.path.is_socket()

    def test_is_fifo(self):
        with pytest.raises(NotImplementedError):
            self.path.is_fifo()

    def test_is_block_device(self):
        with pytest.raises(NotImplementedError):
            self.path.is_block_device()

    def test_is_char_device(self):
        with pytest.raises(NotImplementedError):
            self.path.is_char_device()

    def test_iterdir(self, local_testdir):
        pl_path = Path(local_testdir)

        up_iter = list(self.path.iterdir())
        pl_iter = list(pl_path.iterdir())

        assert len(up_iter) == len(pl_iter)
        assert all(map(lambda x: x.name in [p.name for p in pl_iter], up_iter)) 

    def test_lchmod(self):
        with pytest.raises(NotImplementedError):
            self.path.lchmod(mode=77)

    def test_lstat(self):
        with pytest.raises(NotImplementedError):
            self.path.lstat()

    def test_mkdir(self):
        new_dir = self.path.joinpath('new_dir')
        new_dir.mkdir()
        print(new_dir._accessor.info(new_dir))
        assert new_dir.exists()

    def test_open(self):
        pass

    def test_owner(self):
        with pytest.raises(NotImplementedError):
            self.path.owner()

    def test_read_bytes(self, pathlib_base):
        mock = self.path.joinpath('file2.txt')
        pl = pathlib_base.joinpath('file2.txt')
        assert mock.read_bytes() == pl.read_bytes()

    def test_read_text(self, local_testdir):
        upath = self.path.joinpath('file1.txt')
        assert upath.read_text() == Path(local_testdir).joinpath('file1.txt').read_text()

    def test_readlink(self):
        with pytest.raises(NotImplementedError):
            self.path.readlink()

    @pytest.mark.xfail
    def test_rename(self):
        # need to impliment
        raise False

    def test_replace(self):
        pass

    def test_resolve(self):
        pass

    def test_rglob(self):
        pass



    def test_samefile(self):
        pass

    def test_symlink_to(self):
        pass

    def test_touch_unlink(self):
        path = self.path.joinpath('test_touch.txt')
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
        fn = 'test_write_bytes.txt'
        s = b'hello_world'
        path = self.path.joinpath(fn)
        path.write_bytes(s)
        assert path.read_bytes() == s

    def test_write_text(self, pathlib_base):
        fn = 'test_write_text.txt'
        s = 'hello_world'
        path = self.path.joinpath(fn)
        path.write_text(s)
        assert path.read_text() == s

@pytest.mark.hdfs
class TestUPathHDFS(TestUpath):
    
    @pytest.fixture(autouse=True)
    def path(self, local_testdir, hdfs):
        host, user, port = hdfs
        path = f'hdfs:{local_testdir}'
        self.path = UPath(path,
                          host=host,
                          user=user,
                          port=port)

    def test_chmod(self):
        # todo
        pass


class TestUPathS3(TestUpath):

    @pytest.fixture(autouse=True)
    def path(self, local_testdir, s3):
        anon, s3so = s3
        path = f's3:{local_testdir}'
        self.path = UPath(path, anon=anon, **s3so)

    def test_chmod(self):
        # todo
        pass

    def test_mkdir(self):
        new_dir = self.path.joinpath('new_dir')
        #new_dir.mkdir()
        # mkdir doesnt really do anything. A directory only exists in s3
        # if some file or something is written to it
        f = new_dir.joinpath('test.txt').touch()
        assert new_dir.exists()

    def test_rmdir(self, local_testdir):
        dirname = 'rmdir_test'
        mock_dir = self.path.joinpath(dirname)
        f = mock_dir.joinpath('test.txt').touch()
        mock_dir.rmdir()
        assert not mock_dir.exists()
        with pytest.raises(NotDirectoryError):
            self.path.joinpath('file1.txt').rmdir()

    def test_touch_unlink(self):
        path = self.path.joinpath('test_touch.txt')
        path.touch()
        assert path.exists()
        path.unlink()
        assert not path.exists()

        # should raise FileNotFoundError since file is missing
        with pytest.raises(FileNotFoundError):
            path.unlink()

        # file doesn't exists, but missing_ok is True
        path.unlink(missing_ok=True)

@pytest.mark.hdfs
def test_multiple_backend_paths(local_testdir, s3, hdfs):
    anon, s3so = s3
    path = f's3:{local_testdir}'
    s3_path = UPath(path, anon=anon, **s3so)
    assert s3_path.joinpath('text.txt')._url.scheme == 's3'
    host, user, port = hdfs
    path = f'hdfs:{local_testdir}'
    hdfs_path = UPath(path,
                      host=host,
                      user=user,
                      port=port)
    assert s3_path.joinpath('text1.txt')._url.scheme == 's3'
    
