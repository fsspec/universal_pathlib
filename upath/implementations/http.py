from __future__ import annotations

import sys
from urllib.parse import urlunsplit

from fsspec.asyn import sync

import upath.core


class _HTTPAccessor(upath.core._FSSpecAccessor):
    def __init__(self, parsed_url, *args, **kwargs):
        super().__init__(parsed_url, *args, **kwargs)

    def _format_path(self, path):
        return str(path)


class HTTPPath(upath.core.UPath):
    _default_accessor = _HTTPAccessor

    def is_dir(self):
        try:
            return self._path_type() == "directory"
        except FileNotFoundError:
            return False

    def is_file(self):
        try:
            return self._path_type() == "file"
        except FileNotFoundError:
            return False

    def _path_type(self):
        try:
            next(self.iterdir())
        except (StopIteration, NotADirectoryError):
            return "file"
        else:
            return "directory"

    def _sub_path(self, name):
        """
        `fsspec` returns the full path as `scheme://netloc/<path>` with
        `listdir` and `glob`. However, in `iterdir` and `glob` we only want the
        relative path to `self`.
        """
        complete_address = self._format_parsed_parts(
            None, None, [self._path], url=self._url, **self._kwargs
        )

        if name.startswith(complete_address):
            name = name[len(complete_address) :]  # noqa: E203
        name = name.strip("/")

        return name

    def resolve(
        self: HTTPPath, strict: bool = False, follow_redirects: bool = True
    ) -> HTTPPath:
        """Normalize the path and resolve redirects."""
        # Normalise the path
        resolved_path = super().resolve(strict=strict)

        if follow_redirects:
            # Ensure we have a url
            parsed_url = resolved_path._url
            if parsed_url is None:
                return resolved_path
            else:
                url = parsed_url.geturl()
            # Get the fsspec fs
            fs = resolved_path._accessor._fs
            # Ensure we have a session
            session = sync(fs.loop, fs.set_session)
            # Use HEAD requests if the server allows it, falling back to GETs
            for method in (session.head, session.get):
                r = sync(fs.loop, method, url, allow_redirects=True)
                try:
                    r.raise_for_status()
                except Exception as exc:
                    if method == session.get:
                        raise FileNotFoundError(self) from exc
                else:
                    resolved_path = HTTPPath(str(r.url))
                    break

        return resolved_path

    @property
    def drive(self):
        return f"{self._url.scheme}://{self._url.netloc}"

    @property
    def anchor(self) -> str:
        return self.drive + self.root

    @property
    def parts(self) -> tuple[str, ...]:
        parts = super().parts
        if not parts:
            return ()
        p0, *partsN = parts
        if p0 == "/":
            p0 = self.anchor
        if not partsN and self._url and self._url.path == "/":
            partsN = [""]
        return (p0, *partsN)

    @property
    def path(self) -> str:
        # http filesystems use the full url as path
        if self._url is None:
            raise RuntimeError(str(self))
        return urlunsplit(self._url)


if sys.version_info >= (3, 12):  # noqa
    from itertools import chain
    from urllib.parse import urlsplit

    from upath.core312plus import PathOrStr
    from upath.core312plus import fsspecpathmod
    from upath.core312plus import strip_upath_protocol

    class httppathmod(fsspecpathmod):
        sep: str = "/"
        altsep: str | None = None

        @staticmethod
        def join(__path: PathOrStr, *paths: PathOrStr) -> str:
            path = strip_upath_protocol(__path).removesuffix("/")
            paths = map(strip_upath_protocol, paths)
            sep = httppathmod.sep
            for b in paths:
                if b.startswith(sep):
                    path = b
                elif not path:
                    path += b
                else:
                    path += sep + b
            return path

        @staticmethod
        def splitroot(__path: PathOrStr) -> tuple[str, str, str]:
            # path = strip_upath_protocol(__path)
            url = urlsplit(__path)
            drive = urlunsplit(url._replace(path="", query="", fragment=""))
            path = urlunsplit(url._replace(scheme="", netloc=""))
            root = "/" if path.startswith("/") else ""
            return drive, root, path.removeprefix("/")

        @staticmethod
        def splitdrive(__path: PathOrStr) -> tuple[str, str]:
            path = strip_upath_protocol(__path)
            url = urlsplit(path)
            path = urlunsplit(url._replace(scheme="", netloc=""))
            drive = urlunsplit(url._replace(path="", query="", fragment=""))
            return drive, path

    class HTTPPath(upath.core312plus.UPath):  # noqa
        pathmod = _flavour = httppathmod
        _supports_empty_parts = True

        @property
        def root(self) -> str:
            return super().root or "/"

        def __str__(self):
            return super(upath.core312plus.UPath, self).__str__()

        def is_file(self):
            try:
                next(super().iterdir())
            except (StopIteration, NotADirectoryError):
                return True
            except FileNotFoundError:
                return False
            else:
                return False

        def is_dir(self):
            try:
                next(super().iterdir())
            except (StopIteration, NotADirectoryError):
                return False
            except FileNotFoundError:
                return False
            else:
                return True

        def iterdir(self):
            it = iter(super().iterdir())
            try:
                item0 = next(it)
            except (StopIteration, NotADirectoryError):
                raise NotADirectoryError(str(self))
            except FileNotFoundError:
                raise FileNotFoundError(str(self))
            else:
                yield from chain([item0], it)

        def resolve(
            self: HTTPPath,
            strict: bool = False,
            follow_redirects: bool = True,
        ) -> HTTPPath:
            """Normalize the path and resolve redirects."""
            # Normalise the path
            resolved_path = super().resolve(strict=strict)

            if follow_redirects:
                # Get the fsspec fs
                fs = self.fs
                url = str(self)
                # Ensure we have a session
                session = sync(fs.loop, fs.set_session)
                # Use HEAD requests if the server allows it, falling back to GETs
                for method in (session.head, session.get):
                    r = sync(fs.loop, method, url, allow_redirects=True)
                    try:
                        r.raise_for_status()
                    except Exception as exc:
                        if method == session.get:
                            raise FileNotFoundError(self) from exc
                    else:
                        resolved_path = HTTPPath(str(r.url))
                        break

            return resolved_path
