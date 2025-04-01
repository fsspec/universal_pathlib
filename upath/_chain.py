from __future__ import annotations

from collections.abc import Set
from typing import Any
from typing import NamedTuple
from typing import Self

from fsspec.core import get_filesystem_class
from fsspec.core import split_protocol
from fsspec.registry import known_implementations
from fsspec.registry import registry

__all__ = [
    "ChainSegment",
    "CurrentChainSegment",
    "FSSpecChainParser",
]


class ChainSegment(NamedTuple):
    path: str | None  # support for path passthrough (i.e. simplecache)
    protocol: str
    storage_options: dict[str, Any]


class CurrentChainSegment:
    """holds current chain, source and target segments"""

    __slots__ = (
        "_current",
        "_chain_source",
        "_chain_target",
    )

    def __init__(
        self,
        current: ChainSegment,
        chain_source: list[ChainSegment],
        chain_target: list[ChainSegment],
    ) -> None:
        self._current = current
        self._chain_source = chain_source
        self._chain_target = chain_target

    @property
    def current(self) -> ChainSegment:
        return self._current

    def replace(self, current: ChainSegment) -> Self:
        """replace the current chain segment keeping remaining chain segments"""
        return type(self)(
            current,
            self._chain_source,
            self._chain_target,
        )

    def lshift(self) -> Self:
        """move one chain link towards the source"""
        return type(self)(
            self._chain_source[-1],
            self._chain_source[:-1],
            [self._current, *self._chain_target],
        )

    def rshift(self) -> Self:
        """move one chain link towards the target"""
        return type(self)(
            self._chain_target[0],
            [*self._chain_source, self._current],
            self._chain_target[1:],
        )

    def to_list(self) -> list[ChainSegment]:
        return [*self._chain_source, self._current, *self._chain_target]

    @classmethod
    def from_list(cls, segments: list[ChainSegment], index: int = -1) -> Self:
        index = range(len(segments))[int(index)]
        return cls(
            segments[index],
            segments[:index],
            segments[index + 1 :],
        )


class FSSpecChainParser:
    """parse an fsspec chained urlpath"""

    def __init__(self):
        self.link: str = "::"
        # TODO: recompute when fsspec.registry._registry is updated
        # TODO: add special upath protocols...
        self.known_protocols: Set[str] = set(known_implementations).union(registry)

    def unchain(self, path: str, kwargs: dict[str, Any]) -> list[ChainSegment]:
        """implements same behavior as fsspec.core._un_chain

        two differences:
        1. it sets the urlpath to None for upstream filesystems that passthrough
        2. it checks against the known protocols for exact matches

        TODO: upstream to fsspec

        """
        bits: list[str] = []
        for p in path.split(self.link):
            if "://" in p:  # uri-like, fast-path
                bits.append(p)
            elif p in self.known_protocols:  # exact match a fsspec protocol
                bits.append(f"{p}://")
            else:
                bits.append(p)

        # [[url, protocol, kwargs], ...]
        out: list[ChainSegment] = []
        previous_bit = None
        kwargs = kwargs.copy()
        for bit in reversed(bits):
            protocol = kwargs.pop("protocol", None) or split_protocol(bit)[0] or "file"
            cls = get_filesystem_class(protocol)
            extra_kwargs = cls._get_kwargs_from_urls(bit)
            kws = kwargs.pop(protocol, {})
            if bit is bits[0]:
                kws.update(kwargs)
            kw = dict(**extra_kwargs, **kws)
            bit = cls._strip_protocol(bit)
            if (
                protocol in {"blockcache", "filecache", "simplecache"}
                and "target_protocol" not in kw
            ):
                out.append(ChainSegment(None, protocol, kw))
                bit = previous_bit
            else:
                out.append(ChainSegment(bit, protocol, kw))
            previous_bit = bit
        out.reverse()
        return out

    def chain(self, segments: list[ChainSegment]) -> tuple[str, dict[str, Any]]:
        """returns a chained urlpath from the segments"""
        urlpaths = []
        kwargs = {}
        for segment in segments:
            if segment.path is not None:
                # FIXME: unstrip_protocol requires a fs instance,
                #   which crashes below for filesystems like zip,
                #   tar, that require a fileobject via 'fo' keyword.
                # filesystem(segment.protocol, **segment.storage_options))
                fs_cls = get_filesystem_class(segment.protocol)
                fs = object.__new__(fs_cls)
                super(fs_cls, fs).__init__(**segment.storage_options)
                urlpath = fs.unstrip_protocol(segment.path)
            else:
                urlpath = segment.protocol
            urlpaths.append(urlpath)
            # TODO: ensure roundtrip with unchain behavior
            kwargs[segment.protocol] = segment.storage_options
        return self.link.join(urlpaths), kwargs


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
    segments = CurrentChainSegment.from_list(segments=out1)
    segments0 = segments.lshift()
    assert segments0.current.protocol == "zip"

    # try to switch out zip path
    segments1 = segments0.replace(segments0.current._replace(path="/newfile.csv"))
    new_path, new_kw = FSSpecChainParser().chain(segments1.to_list())
    print(new_path, new_kw)
