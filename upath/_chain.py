from __future__ import annotations

import sys
import warnings
from collections import defaultdict
from collections import deque
from collections.abc import MutableMapping
from collections.abc import Sequence
from collections.abc import Set
from typing import TYPE_CHECKING
from typing import Any
from typing import NamedTuple

if TYPE_CHECKING:
    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self

from upath._flavour import WrappedFileSystemFlavour
from upath._protocol import get_upath_protocol
from upath.registry import available_implementations

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


class FSSpecChainParser:
    """parse an fsspec chained urlpath"""

    def __init__(self) -> None:
        self.link: str = "::"
        self.known_protocols: Set[str] = set()

    def unchain(self, path: str, kwargs: dict[str, Any]) -> list[ChainSegment]:
        """implements same behavior as fsspec.core._un_chain

        two differences:
        1. it sets the urlpath to None for upstream filesystems that passthrough
        2. it checks against the known protocols for exact matches

        """
        # TODO: upstream to fsspec
        first_bit_protocol: str | None = kwargs.pop("protocol", None)
        it_bits = iter(path.split(self.link))
        bits: list[str]
        if first_bit_protocol is not None:
            bits = [next(it_bits)]
        else:
            bits = []
        for p in it_bits:
            if "://" in p:  # uri-like, fast-path
                bits.append(p)
            elif "/" in p:  # path-like, fast-path
                bits.append(p)
            elif p in self.known_protocols:  # exact match a fsspec protocol
                bits.append(f"{p}://")
            elif p in (m := set(available_implementations(fallback=True))):
                self.known_protocols = m
                bits.append(f"{p}://")
            else:
                bits.append(p)

        # [[url, protocol, kwargs], ...]
        out: list[ChainSegment] = []
        previous_bit: str | None = None
        kwargs = kwargs.copy()
        first_bit_idx = len(bits) - 1
        for idx, bit in enumerate(reversed(bits)):
            if idx == first_bit_idx:
                protocol = first_bit_protocol or get_upath_protocol(bit) or ""
            else:
                protocol = get_upath_protocol(bit) or ""
            flavour = WrappedFileSystemFlavour.from_protocol(protocol)
            extra_kwargs = flavour.get_kwargs_from_url(bit)
            kws = kwargs.pop(protocol, {})
            if bit is bits[0]:
                kws.update(kwargs)
            kw = dict(**extra_kwargs)
            kw.update(kws)
            if "target_protocol" in kw:
                kw.setdefault("target_options", {})
            bit = flavour.strip_protocol(bit) or flavour.root_marker
            if (
                protocol in {"blockcache", "filecache", "simplecache"}
                and "target_protocol" not in kw
            ):
                out.append(ChainSegment(None, protocol, kw))
                if previous_bit is not None:
                    bit = previous_bit
            else:
                out.append(ChainSegment(bit, protocol, kw))
            previous_bit = bit
        out.reverse()
        return out

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
    out1 = FSSpecChainParser().unchain(chained_path, chained_kw)

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
