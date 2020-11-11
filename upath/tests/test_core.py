import pytest

from upath import UPath


class TestUpath:

    @pytest.mark.xfail
    def test_cwd(self, afs):
        # should raise not implimented if UniversalPath
        path = UPath('/')
        print(path.cwd())
        assert False
        
    @pytest.mark.xfail
    def test_home(self, afs):
        # should raise not implimented if UniversalPath
        path = UPath('/')
        print(path.home())
        assert False


    def test_stat(self, afs):
        path = UPath('mock:top_level')
        print(path.stat())
        
        path = UPath('/tmp')
        print(path.stat())
        assert False
        pass

    def test_chmod(self, afs):
        path = UPath('mock:/')
        with pytest.raises(NotImplementedError):
            path.chmod(777)

    @pytest.mark.parametrize('url, expected', [('mock:top_level', True), ('mock:/fake', False)])
    def test_exists(self, afs, url, expected):
        path = UPath(url)
        assert path.exists() == expected

    def test_expanduser(self, afs):
        path = UPath('mock:/')
        with pytest.raises(NotImplementedError):
            path.expanduser()

    def test_glob(self, afs):
        pass

    def test_group(self, afs):
        pass

    def test_is_dir(self, afs):
        path = UPath('mock:top_level')
        assert path.is_dir()

        path = UPath('mock:misc/foo.txt')
        assert not path.is_dir()

    def test_is_file(self, afs):
        path = UPath('mock:misc/foo.txt')
        assert path.is_file()

        path = UPath('mock:top_level')
        assert not path.is_file()
        

    def test_is_mount(self, afs):
        pass

    def test_is_symlink(self, afs):
        pass

    def test_is_socket(self, afs):
        pass

    def test_is_fifo(self, afs):
        pass

    def test_is_block_device(self, afs):
        pass

    def test_is_char_device(self, afs):
        pass

    def test_iterdir(self, afs):
        pass

    def test_lchmod(self, afs):
        pass

    def test_lstat(self, afs):
        pass

    def test_mkdir(self, afs):
        pass

    def test_open(self, afs):
        pass

    def test_owner(self, afs):
        pass

    def test_read_bytes(self, afs):
        pass

    def test_read_text(self, afs):
        pass

    def test_readlink(self, afs):
        pass

    def test_rename(self, afs):
        pass

    def test_replace(self, afs):
        pass

    def test_resolve(self, afs):
        pass

    def test_rglob(self, afs):
        pass

    def test_rmdir(self, afs):
        pass

    def test_samefile(self, afs):
        pass

    def test_symlink_to(self, afs):
        pass

    def test_touch(self, afs):
        pass

    def test_unlink(self, afs):
        pass

    def test_link_to(self, afs):
        pass

    def test_write_bytes(self, afs):
        pass

    def test_write_text(self, afs):
        pass

