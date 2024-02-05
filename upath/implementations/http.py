from __future__ import annotations

from itertools import chain

from fsspec.asyn import sync

from upath._compat import FSSpecAccessorShim as _FSSpecAccessorShim
from upath._flavour import FSSpecFlavour as _FSSpecFlavour
from upath.core import UPath

__all__ = ["HTTPPath"]

# accessors are deprecated
_HTTPAccessor = _FSSpecAccessorShim


class HTTPPath(UPath):
    _flavour = _FSSpecFlavour(
        join_like_urljoin=True,
        supports_empty_parts=True,
        supports_netloc=True,
        supports_query_parameters=True,
        supports_fragments=True,
    )

    @property
    def root(self) -> str:
        return super().root or "/"

    def __str__(self):
        return super(UPath, self).__str__()

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
