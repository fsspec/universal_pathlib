from pathlib import Path

import pytest

from upath import UPath
from upath.errors import NotDirectoryError


@pytest.fixture()
def mock_base(testingdir):
    return UPath(f'mock:{testingdir}')

@pytest.fixture()
def pathlib_base(testingdir):
    return Path(testingdir)


class TestUpath:

    def test_cwd(self, mock_base):
        with pytest.raises(NotImplementedError):
            mock_base.cwd()
        
    def test_home(self, mock_base):
        with pytest.raises(NotImplementedError):
            mock_base.home()


    def test_stat(self, mock_base):
        stat = mock_base.stat()
        assert all(map(lambda x: x in stat, ['type', 'name']))

        
    def test_chmod(self, mock_base):
        with pytest.raises(NotImplementedError):
            mock_base.joinpath('file1.txt').chmod(777)

    @pytest.mark.parametrize('url, expected', [('file1.txt', True), ('fakefile.txt', False)])
    def test_exists(self, mock_base, url, expected):
        path = mock_base.joinpath(url)
        assert path.exists() == expected

    def test_expanduser(self, mock_base):
        with pytest.raises(NotImplementedError):
            mock_base.expanduser()

    def test_glob(self, mock_base, pathlib_base):
        mock_glob = list(mock_base.glob('**.txt'))
        path_glob = list(pathlib_base.glob('**/*.txt'))

        print(mock_glob)
        print(path_glob)

        assert len(mock_glob) == len(path_glob)
        assert all(map(lambda m: m.path in [str(p) for p in path_glob], mock_glob))
        # for m, p in zip(mock_glob, path_glob):
        #     assert m.path == str(p)

    def test_group(self, mock_base):
        with pytest.raises(NotImplementedError):
            mock_base.group()

    def test_is_dir(self, testingdir):
        path = UPath('mock:' + testingdir)
        assert path.is_dir()

        path = UPath(f'mock:{testingdir}/file1.txt')
        assert not path.is_dir()

    def test_is_file(self, testingdir):
        path = UPath(f'mock:{testingdir}/file1.txt')
        assert path.is_file()

        path = UPath(f'mock:{testingdir}')
        assert not path.is_file()

    def test_is_mount(self, mock_base):
        with pytest.raises(NotImplementedError):
            mock_base.is_mount()

    def test_is_symlink(self, mock_base):
        with pytest.raises(NotImplementedError):
            mock_base.is_symlink()

    def test_is_socket(self, mock_base):
        with pytest.raises(NotImplementedError):
            mock_base.is_socket()

    def test_is_fifo(self, mock_base):
        with pytest.raises(NotImplementedError):
            mock_base.is_fifo()

    def test_is_block_device(self, mock_base):
        with pytest.raises(NotImplementedError):
            mock_base.is_block_device()

    def test_is_char_device(self, mock_base):
        with pytest.raises(NotImplementedError):
            mock_base.is_char_device()

    def test_iterdir(self, testingdir):
        path = UPath(f'mock:{testingdir}')
        pl_path = Path(testingdir)

        up_iter = list(path.iterdir())
        pl_iter = list(path.iterdir())

        assert len(up_iter) == len(pl_iter)
        assert all(map(lambda x: x.name in [p.name for p in pl_iter], up_iter)) 

    def test_lchmod(self, mock_base):
        with pytest.raises(NotImplementedError):
            mock_base.lchmod(mode=77)

    def test_lstat(self, mock_base):
        with pytest.raises(NotImplementedError):
            mock_base.lstat()

    def test_mkdir(self, mock_base):
        new_dir = mock_base.joinpath('new_dir')
        new_dir.mkdir()
        assert new_dir.exists()

    def test_open(self, testingdir):
        pass

    def test_owner(self, mock_base):
        with pytest.raises(NotImplementedError):
            mock_base.owner()

    def test_read_bytes(self, mock_base, pathlib_base):
        mock = mock_base.joinpath('file2.txt')
        pl = pathlib_base.joinpath('file2.txt')
        assert mock.read_bytes() == pl.read_bytes()

    def test_read_text(self, testingdir):
        upath = UPath(f'mock:{testingdir}/file1.txt')
        assert upath.read_text() == Path(testingdir).joinpath('file1.txt').read_text()

    def test_readlink(self, mock_base):
        with pytest.raises(NotImplementedError):
            mock_base.readlink()

    @pytest.mark.xfail
    def test_rename(self, testingdir):
        # need to impliment
        raise False

    def test_replace(self, testingdir):
        pass

    def test_resolve(self, testingdir):
        pass

    def test_rglob(self, testingdir):
        pass

    def test_rmdir(self, mock_base, pathlib_base):
        dirname = 'rmdir_test'
        pl_dir = pathlib_base.joinpath(dirname)
        pl_dir.mkdir()
        assert pl_dir.exists()
        mock_dir = mock_base.joinpath(dirname)
        mock_dir.rmdir()
        assert not pl_dir.exists()

        with pytest.raises(NotDirectoryError):
            mock_base.joinpath('file1.txt').rmdir()

    def test_samefile(self, testingdir):
        pass

    def test_symlink_to(self, testingdir):
        pass

    def test_touch(self, mock_base):
        path = mock_base.joinpath('test_touch.txt')
        path.touch()

        pl_path = Path(path.path)
        assert pl_path.exists()

    def test_unlink(self, mock_base, pathlib_base):
        fn = 'unlink_test.txt'
        pl = pathlib_base.joinpath(fn)
        pl.touch()
        assert pl.exists()
        mock = mock_base.joinpath(fn)
        mock.unlink()
        assert not pl.exists()

        # should raise FileNotFoundError since file is missing
        with pytest.raises(FileNotFoundError):
            mock.unlink()

        # file doesn't exists, but missing_ok is True
        mock.unlink(missing_ok=True)


    def test_link_to(self, testingdir):
        pass

    def test_write_bytes(self, mock_base, pathlib_base):
        fn = 'test_write_bytes.txt'
        s = b'hello_world'
        mock_base.joinpath(fn).write_bytes(s)
        assert pathlib_base.joinpath(fn).read_bytes() == s


    def test_write_text(self, mock_base, pathlib_base):
        fn = 'test_write_text.txt'
        s = b'hello_world'
        mock_base.joinpath(fn).write_bytes(s)
        assert pathlib_base.joinpath(fn).read_bytes() == s



def test_hdfs(hdfs_test_client):
    host, user, port = hdfs_test_client
    path = UPath('hdfs:/', host=host, user=user, port=port, driver='libhdfs3')
    assert path.exists()

