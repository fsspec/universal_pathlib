from __future__ import annotations

import sys
import warnings
from collections import defaultdict
from collections import deque
from collections.abc import Iterator
from collections.abc import MutableMapping
from collections.abc import Sequence
from collections.abc import Set
from itertools import zip_longest
from typing import TYPE_CHECKING
from typing import Any
from typing import NamedTuple

from upath._flavour import WrappedFileSystemFlavour
from upath._protocol import get_upath_protocol
from upath.registry import available_implementations
from upath.types import UNSET_DEFAULT

if TYPE_CHECKING:
    if sys.version_info >= (3, 11):
        from typing import Never
        from typing import Self
    else:
        from typing_extensions import Never
        from typing_extensions import Self

__all__ = [
    "ChainSegment",
    "Chain",
    "FSSpecChainParser",
    "DEFAULT_CHAIN_PARSER",
]


class ChainSegment(NamedTuple):
    path: str | None  # support for path passthrough (i.e. simplecache)
    protocol: str
    storage_options: dict[str, Any]


class Chain:
    """holds current chain segments"""

    __slots__ = (
        "_segments",
        "_index",
    )

    def __init__(
        self,
        *segments: ChainSegment,
        index: int = 0,
    ) -> None:
        if not (0 <= index < len(segments)):
            raise ValueError("index must be between 0 and len(segments)")
        self._segments = segments
        self._index = index

    def __repr__(self) -> str:
        args = ", ".join(map(repr, self._segments))
        if self._index != 0:
            args += f", index={self._index}"
        return f"{type(self).__name__}({args})"

    @property
    def current(self) -> ChainSegment:
        return self._segments[self._index]

    @property
    def _path_index(self) -> int:
        for idx, segment in enumerate(self._segments[self._index :], start=self._index):
            if segment.path is not None:
                return idx
        raise IndexError("No target path found")

    @property
    def active_path(self) -> str:
        path = self._segments[self._path_index].path
        if path is None:
            raise RuntimeError
        return path

    @property
    def active_path_protocol(self) -> str:
        return self._segments[self._path_index].protocol

    def replace(
        self,
        *,
        path: str | None = None,
        protocol: str | None = None,
        storage_options: dict[str, Any] | None = None,
    ) -> Self:
        """replace the current chain segment keeping remaining chain segments"""
        segments = self.to_list()
        index = self._index

        replacements: MutableMapping[int, dict[str, Any]] = defaultdict(dict)
        if protocol is not None:
            replacements[index]["protocol"] = protocol
        if storage_options is not None:
            replacements[index]["storage_options"] = storage_options
        if path is not None:
            replacements[self._path_index]["path"] = path

        for idx, items in replacements.items():
            segments[idx] = segments[idx]._replace(**items)

        return type(self)(*segments, index=index)

    def to_list(self) -> list[ChainSegment]:
        """return a list of chain segments unnesting target_* segments"""
        queue = deque(self._segments)
        segments = []
        while queue:
            segment = queue.popleft()
            if (
                "target_protocol" in segment.storage_options
                and "fo" in segment.storage_options
            ):
                storage_options = segment.storage_options.copy()
                target_options = storage_options.pop("target_options", {})
                target_protocol = storage_options.pop("target_protocol")
                fo = storage_options.pop("fo")
                queue.appendleft(ChainSegment(fo, target_protocol, target_options))
                segments.append(
                    ChainSegment(segment.path, segment.protocol, storage_options)
                )
            elif not segments or segment != segments[-1]:
                segments.append(segment)
        return segments

    @classmethod
    def from_list(cls, segments: list[ChainSegment], index: int = 0) -> Self:
        return cls(*segments, index=index)

    def nest(self) -> ChainSegment:
        """return a nested target_* structure"""
        # see: fsspec.core.url_to_fs
        inkwargs: dict[str, Any] = {}
        # Reverse iterate the chain, creating a nested target_* structure
        chain = self._segments
        _prev = chain[-1].path
        for i, ch in enumerate(reversed(chain)):
            urls, protocol, kw = ch
            if urls is None:
                urls = _prev
            _prev = urls
            if i == len(chain) - 1:
                inkwargs = {**kw, **inkwargs}
                continue
            inkwargs["target_options"] = {**kw, **inkwargs}
            inkwargs["target_protocol"] = protocol
            inkwargs["fo"] = urls  # codespell:ignore fo
        urlpath, protocol, _ = chain[0]
        return ChainSegment(urlpath, protocol, inkwargs)


def _iter_fileobject_protocol_options(
    fileobject: str | None,
    protocol: str,
    storage_options: dict[str, Any],
    /,
) -> Iterator[tuple[str | None, str, dict[str, Any]]]:
    """yields fileobject, protocol and remaining storage options"""
    so = storage_options.copy()
    while "target_protocol" in so:
        t_protocol = so.pop("target_protocol", "")
        t_fileobject = so.pop("fo", None)  # codespell:ignore fo
        t_so = so.pop("target_options", {})
        yield fileobject, protocol, so
        fileobject, protocol, so = t_fileobject, t_protocol, t_so
    yield fileobject, protocol, so


class FSSpecChainParser:
    """parse an fsspec chained urlpath"""

    def __init__(self) -> None:
        self.link: str = "::"
        self.known_protocols: Set[str] = set()

    def unchain(
        self,
        path: str,
        _deprecated_storage_options: Never = UNSET_DEFAULT,
        /,
        *,
        protocol: str | None = None,
        storage_options: dict[str, Any] | None = None,
    ) -> list[ChainSegment]:
        """implements same behavior as fsspec.core._un_chain

        two differences:
        1. it sets the urlpath to None for upstream filesystems that passthrough
        2. it checks against the known protocols for exact matches

        """
        if _deprecated_storage_options is not UNSET_DEFAULT:
            warnings.warn(
                "passing storage_options as positional argument is deprecated, "
                "pass as keyword argument instead",
                DeprecationWarning,
                stacklevel=2,
            )
            if storage_options is not None:
                raise ValueError(
                    "cannot pass storage_options both positionally and as keyword"
                )
            storage_options = _deprecated_storage_options
            protocol = protocol or storage_options.get("protocol")
        if storage_options is None:
            storage_options = {}

        segments: list[ChainSegment] = []
        path_bit: str | None
        next_path_overwrite: str | None = None
        for proto0, bit in zip_longest([protocol], path.split(self.link)):
            # get protocol and path_bit
            if (
                "://" in bit  # uri-like, fast-path (redundant)
                or "/" in bit  # path-like, fast-path
            ):
                proto = get_upath_protocol(bit, protocol=proto0)
                flavour = WrappedFileSystemFlavour.from_protocol(proto)
                path_bit = flavour.strip_protocol(bit)
                extra_so = flavour.get_kwargs_from_url(bit)
            elif bit in self.known_protocols and (
                proto0 is None or bit == proto0
            ):  # exact match a fsspec protocol
                proto = bit
                path_bit = ""
                extra_so = {}
            elif bit in (m := set(available_implementations(fallback=True))) and (
                proto0 is None or bit == proto0
            ):
                self.known_protocols = m
                proto = bit
                path_bit = ""
                extra_so = {}
            else:
                proto = get_upath_protocol(bit, protocol=proto0)
                flavour = WrappedFileSystemFlavour.from_protocol(proto)
                path_bit = flavour.strip_protocol(bit)
                extra_so = flavour.get_kwargs_from_url(bit)
            if proto in {"blockcache", "filecache", "simplecache"}:
                if path_bit:
                    next_path_overwrite = path_bit
                path_bit = None
            elif next_path_overwrite is not None:
                path_bit = next_path_overwrite
                next_path_overwrite = None
            segments.append(ChainSegment(path_bit, proto, extra_so))

        root_so = segments[0].storage_options
        for segment, proto_fo_so in zip_longest(
            segments,
            _iter_fileobject_protocol_options(
                path_bit if segments else None,
                protocol or "",
                storage_options,
            ),
        ):
            t_fo, t_proto, t_so = proto_fo_so or (None, "", {})
            if segment is None:
                if next_path_overwrite is not None:
                    t_fo = next_path_overwrite
                    next_path_overwrite = None
                segments.append(ChainSegment(t_fo, t_proto, t_so))
            else:
                proto = segment.protocol
                # check if protocol is consistent with storage options
                if t_proto and t_proto != proto:
                    raise ValueError(
                        f"protocol {proto!r} collides with target_protocol {t_proto!r}"
                    )
                # update the storage_options
                segment.storage_options.update(root_so.pop(proto, {}))
                segment.storage_options.update(t_so)

        return segments

    def chain(self, segments: Sequence[ChainSegment]) -> tuple[str, dict[str, Any]]:
        """returns a chained urlpath from the segments"""
        urlpaths = []
        kwargs = {}
        for segment in segments:
            if segment.protocol and segment.path is not None:
                # FIXME: currently unstrip_protocol is only implemented by
                #   AbstractFileSystem, LocalFileSystem, and OSSFileSystem
                #   so to make this work we just implement it ourselves here.
                #   To do this properly we would need to instantiate the
                #   filesystem with its storage options and call
                #   fs.unstrip_protocol(segment.path)
                if segment.path.startswith(f"{segment.protocol}:/"):
                    urlpath = segment.path
                else:
                    urlpath = f"{segment.protocol}://{segment.path}"
            elif segment.protocol:
                urlpath = segment.protocol
            elif segment.path is not None:
                urlpath = segment.path
            else:
                warnings.warn(
                    f"skipping invalid segment {segment}",
                    RuntimeWarning,
                    stacklevel=2,
                )
                continue
            urlpaths.append(urlpath)
            # TODO: ensure roundtrip with unchain behavior
            if segment.storage_options:
                kwargs[segment.protocol] = segment.storage_options
        return self.link.join(urlpaths), kwargs


DEFAULT_CHAIN_PARSER = FSSpecChainParser()


if __name__ == "__main__":
    from pprint import pp

    from fsspec.core import _un_chain

    chained_path = "simplecache::zip://haha.csv::gcs://bucket/file.zip"
    chained_kw = {"zip": {"allowZip64": False}}
    print(chained_path, chained_kw)
    out0 = _un_chain(chained_path, chained_kw)
    out1 = FSSpecChainParser().unchain(chained_path, storage_options=chained_kw)

    pp(out0)
    pp(out1)

    rechained_path, rechained_kw = FSSpecChainParser().chain(out1)
    print(rechained_path, rechained_kw)

    # UPath should store segments and access the path to operate on
    # through segments.current.path
    segments0 = Chain.from_list(segments=out1, index=1)
    assert segments0.current.protocol == "zip"

    # try to switch out zip path
    segments1 = segments0.replace(path="/newfile.csv")
    new_path, new_kw = FSSpecChainParser().chain(segments1.to_list())
    print(new_path, new_kw)
