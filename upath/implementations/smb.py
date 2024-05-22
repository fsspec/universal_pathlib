import smbprotocol.exceptions

from upath import UPath


class SMBPath(UPath):
    __slots__ = ()

    @property
    def path(self):
        return "/" + super().path

    def mkdir(self, mode=0o777, parents=False, exist_ok=False):
        # smbclient does not support setting mode externally
        if parents and not exist_ok and self.exists():
            raise FileExistsError(str(self))
        try:
            self.fs.mkdir(
                self.path,
                create_parents=parents,
            )
        except smbprotocol.exceptions.SMBOSError:
            if not exist_ok:
                raise FileExistsError(str(self))
            if not self.is_dir():
                raise FileExistsError(str(self))

    def iterdir(self):
        if not self.is_dir():
            raise NotADirectoryError(str(self))
        else:
            return super().iterdir()
