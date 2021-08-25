import pytest
import os
from contextlib import contextmanager

from upath import UPath
from upath.implementations.gcs import GCSPath

from upath.tests.utils import my_vcr, TEST_BUCKET, TEST_PROJECT, RECORD_MODE, GOOGLE_TOKEN, gcs_maker, csv_files, TEST_BUCKET_2
import re


import logging


# class TestGCSPath(BaseTests):
class TestGCSPath():
    test_file = list(csv_files.keys())[0]

    @my_vcr.use_cassette(match=["all"])
    @pytest.fixture(autouse=True)
    def path(self, local_testdir):
        scheme = f'gs://'
        bucket = TEST_BUCKET
        self.path = UPath(f'{scheme}{bucket}', project=TEST_PROJECT, token=GOOGLE_TOKEN)


    def test_path_construction(self):
        scheme = f'gs://'
        bucket = TEST_BUCKET
        upath_ = UPath(f'{scheme}{bucket}', token=GOOGLE_TOKEN)
        assert str(upath_) == f'{scheme}{TEST_BUCKET}/'

    def test_is_GCSPath(self):
        assert isinstance(self.path, GCSPath)


    # # # def prepare_file_system(self):
    # # #     self.make_top_folder()
    # # #     self.make_test_files()

    # # # def make_top_folder(self):
    # # #     self.path.mkdir(parents=True, exist_ok=True)

    # # # def make_test_files(self):
    # # #     folder1 = self.path.joinpath("folder1")
    # # #     folder1.mkdir(exist_ok=True)
    # # #     folder1_files = ["file1.txt", "file2.txt"]
    # # #     for f in folder1_files:
    # # #         p = folder1.joinpath(f)
    # # #         p.touch()
    # # #         p.write_text(f)

    # # #     file1 = self.path.joinpath("file1.txt")
    # # #     file1.touch()
    # # #     file1.write_text("hello world")
    # # #     file2 = self.path.joinpath("file2.txt")
    # # #     file2.touch()
    # # #     file2.write_bytes(b"hello world")

    def test_cwd(self):
        with pytest.raises(NotImplementedError):
            self.path.cwd()

    def test_home(self):
        with pytest.raises(NotImplementedError):
            self.path.home()

    @my_vcr.use_cassette(match=["all"])
    def test_stat(self):
        with gcs_maker() as gcs:
            stat = self.path.stat()
            assert stat

    # @my_vcr.use_cassette(match=["all"])
    # def test_chmod(self):
    #     with pytest.raises(NotImplementedError):
    #         self.path.joinpath(self.test_file).chmod(777)

    # @my_vcr.use_cassette(match=["all"])
    # @pytest.mark.parametrize(
    #     "url, expected", [(list(csv_files.keys())[0], True), ("fakefile.txt", False)]
    # )
    # def test_exists(self, url, expected):
    #     path = self.path.joinpath(url)
    #     assert path.exists() == expected

    # @my_vcr.use_cassette(match=["all"])
    # def test_expanduser(self):
    #     with pytest.raises(NotImplementedError):
    #         self.path.expanduser()

    # @my_vcr.use_cassette(match=["all"])
    # def test_glob(self):
    #     mock_glob = list(self.path.glob("**.csv"))
    #     path_glob = self.path.fs.glob(f"{TEST_BUCKET}/**.csv")

    #     assert len(mock_glob) == len(path_glob)
    #     assert all(
    #         map(
    #             lambda m: m.path
    #             in [re.sub(r'(^.*)(\/.*$)',r'\2', p) for p in path_glob],
    #             mock_glob,
    #         )
    #     )

    # @my_vcr.use_cassette(match=["all"])
    # def test_group(self):
    #     with pytest.raises(NotImplementedError):
    #         self.path.group()

    # @my_vcr.use_cassette(match=["all"])
    # def test_is_dir(self):
    #     assert self.path.is_dir()

    #     path = self.path.joinpath(self.test_file)
    #     assert not path.is_dir()

    # @my_vcr.use_cassette(match=["all"])
    # def test_is_file(self):
    #     path = self.path.joinpath(self.test_file)
    #     assert path.is_file()
    #     assert not self.path.is_file()

    # @my_vcr.use_cassette(match=["all"])
    # def test_is_mount(self):
    #     with pytest.raises(NotImplementedError):
    #         self.path.is_mount()

    # @my_vcr.use_cassette(match=["all"])
    # def test_is_symlink(self):
    #     with pytest.raises(NotImplementedError):
    #         self.path.is_symlink()

    # @my_vcr.use_cassette(match=["all"])
    # def test_is_socket(self):
    #     with pytest.raises(NotImplementedError):
    #         self.path.is_socket()

    # @my_vcr.use_cassette(match=["all"])
    # def test_is_fifo(self):
    #     with pytest.raises(NotImplementedError):
    #         self.path.is_fifo()

    # def test_is_block_device(self):
    #     with pytest.raises(NotImplementedError):
    #         self.path.is_block_device()

    # @my_vcr.use_cassette(match=["all"])
    # def test_is_char_device(self):
    #     with pytest.raises(NotImplementedError):
    #         self.path.is_char_device()

    # @my_vcr.use_cassette(match=["all"])
    # def test_iterdir(self, gcs):
    #     up_iter = list(self.path.iterdir())
    #     fs_iter = gcs.ls(TEST_BUCKET)

    #     for x in up_iter:
    #         assert x.exists()

    #     assert len(up_iter) == len(fs_iter)
    #     assert all(
    #         map(
    #             lambda m: m.path
    #             in [re.sub(r'(^.*)(\/.*$)',r'\2', p) for p in fs_iter],
    #             up_iter,
    #         )
    #     )
    #     assert next(self.path.parent.iterdir()).exists()

    # @my_vcr.use_cassette(match=["all"])
    # def test_lchmod(self):
    #     with pytest.raises(NotImplementedError):
    #         self.path.lchmod(mode=77)

    # @my_vcr.use_cassette(match=["all"])
    # def test_lstat(self):
    #     with pytest.raises(NotImplementedError):
    #         self.path.lstat()

    # @my_vcr.use_cassette(match=["all"])
    # def test_mkdir_bucket(self, gcs):
    #     """test creading a bucket via mkdir
    #     if the path leads to a bucket that doesn't exist, it will
    #     be created
    #     """
    #     # create a temporary bucket
    #     path = UPath(f'gs://{TEST_BUCKET_2}', project=TEST_PROJECT, token=GOOGLE_TOKEN)
    #     path.mkdir()

    #     exist = False
    #     if TEST_BUCKET_2 in path.fs.ls('') or f'{TEST_BUCKET_2}/' in path.fs.ls(''):
    #         exist = True

    #     # clean up temporary bucket
    #     path.fs.rmdir(TEST_BUCKET_2)
    #     assert exist

    # @my_vcr.use_cassette(match=["all"])
    # def test_mkdir_folder(self, gcs):
    #     """test creating an empty folder inside of existing
    #     bucket - not possible on gcs, folders must contain files"""
    #     new_dir = self.path.joinpath("new_dir")
    #     new_dir.mkdir()
    #     # ensure that the folder doesn't exist
    #     assert not new_dir.fs.isdir(new_dir)


    # def test_open(self):
    #     pass

    # def test_owner(self):
    #     with pytest.raises(NotImplementedError):
    #         self.path.owner()

    # @my_vcr.use_cassette(match=["all"])
    # def test_read_bytes(self, gcs):
    #     mock = self.path.joinpath(self.test_file)
    #     with self.path.fs.open(mock) as f:
    #         # f is now a real file-like object holding resources
    #         contents = f.read()
    #         assert mock.read_bytes() == contents

    # @my_vcr.use_cassette(match=["all"])
    # def test_read_text(self):
    #     upath = self.path.joinpath(self.test_file)
    #     with self.path.fs.open(upath) as f:
    #         # f is now a real file-like object holding resources
    #         contents = f.read().decode("utf-8") 
    #         assert upath.read_text() == contents

    # def test_readlink(self):
    #     with pytest.raises(NotImplementedError):
    #         self.path.readlink()

    # @pytest.mark.xfail
    # def test_rename(self):
    #     # need to impliment
    #     raise False

    # def test_replace(self):
    #     pass

    # def test_resolve(self):
    #     pass

    # def test_rglob(self):
    #     pass

    # def test_samefile(self):
    #     pass

    # def test_symlink_to(self):
    #     pass

    # @my_vcr.use_cassette(match=["all"])
    # def test_touch_unlink(self):
    #     path = self.path.joinpath("test_touch.txt")
    #     path.touch()
    #     path.fs.invalidate_cache()
    #     # import pdb ; pdb.set_trace()
    #     # assert path.exists()
    #     assert path.fs.isfile(path)
    #     path.unlink()
    #     path.fs.invalidate_cache()
    #     assert not path.exists()

    #     # should raise FileNotFoundError since file is missing
    #     with pytest.raises(FileNotFoundError):
    #         path.unlink()

    #     # file doesn't exist, but missing_ok is True
    #     path.unlink(missing_ok=True)

    # def test_link_to(self):
    #     pass

    # @my_vcr.use_cassette(match=["all"])
    # def test_write_bytes(self, gcs):
    #     fn = "test_write_bytes.txt"
    #     s = b"hello_world"
    #     path = self.path.joinpath(fn)
    #     path.write_bytes(s)
    #     assert path.read_bytes() == s

    # @my_vcr.use_cassette(match=["all"])
    # def test_write_text(self, gcs):
    #     fn = "test_write_text.txt"
    #     s = "hello_world"
    #     path = self.path.joinpath(fn)
    #     path.write_text(s)
    #     assert path.read_text() == s

    # @my_vcr.use_cassette(match=["all"])
    # def test_fsspec_compat(self):
    #     with gcs_maker() as gcs:
    #         fs = self.path.fs
    #         content = b"a,b,c\n1,2,3\n4,5,6"
    #         # write with upath, read with fsspec
    #         path1 = self.path.joinpath('output1.csv')
    #         path1.write_bytes(content)
    #         with fs.open(path1) as f:
    #             assert f.read() == content
    #         path1.unlink()

    #         # write with fsspec, read with upath
    #         path2 = self.path.joinpath('output2.csv')
    #         with fs.open(path2, "wb") as f:
    #             f.write(content)
    #         assert path2.read_bytes() == content
    #         path2.unlink()



# @my_vcr.use_cassette(match=["all"])
# def test_simple():
#     assert not GoogleCredentials.tokens
#     # import pdb; pdb.set_trace()
#     gcs = GCSFileSystem(TEST_PROJECT, token=GOOGLE_TOKEN)
#     # # gcs.invalidate_cache()
#     # gcs.ls(TEST_BUCKET)  # no error
#     # print(gcs.ls(TEST_BUCKET))
#     # gcs.ls("/" + TEST_BUCKET)  # OK to lead with '/'
#     # gcs.invalidate_cache()

# @my_vcr.use_cassette(match=["all"])
# def test_ls():
#     assert not GoogleCredentials.tokens
#     # import pdb; pdb.set_trace()
#     gcs = GCSFileSystem(TEST_PROJECT, token=GOOGLE_TOKEN)
#     gcs.ls(TEST_BUCKET)  # no error
#     gcs.ls("/" + TEST_BUCKET)  # OK to lead with '/'


# def test_creating_gspath_with_bucket():
#     path = UPath("gs://", bucket="bucket")
#     assert str(path) == "gs://bucket/"