from __future__ import annotations

from multiprocessing.sharedctypes import Synchronized, SynchronizedArray
from tempfile import _TemporaryFileWrapper
from typing import Protocol, TypeVar, TypeAlias, NamedTuple, TYPE_CHECKING
from unittest.mock import _patch


if TYPE_CHECKING:
    from analysis.plugin import AnalysisPluginV0

KT = TypeVar('KT', str, tuple, bytes)  # generic key type
VT = TypeVar('VT')  # generic value type

# NamedTemporaryFile is actually a function that returns an instance of class _TemporaryFileWrapper, so it can't be
# used for type hinting
TmpFile: TypeAlias = _TemporaryFileWrapper

# multiprocessing.Value returns "SynchronizedBase[Any]" which has no attribute "value". This is a known bug in
# mypy, see https://github.com/python/typeshed/issues/8799 -> ignore assignment and treat as Synchronized
MpValue: TypeAlias = Synchronized
MpArray: TypeAlias = SynchronizedArray

# comparison ID: Represents one comparison between two or more firmwares.
# Consists of UIDs with semicolons in-between (e.g. "uid1;uid2;...")
CompId: TypeAlias = str

# a UID (unique identifier) "{sha256 hash}_{file size in bytes}" for a byte string (i.e. the contents of a file)
UID: TypeAlias = str

# unittest patch() is a function and returns a private _patch class
Patch: TypeAlias = _patch


class AnalysisPluginInfo(NamedTuple):
    description: str
    mandatory: bool
    presets: dict
    version: str
    dependencies: list[str]
    blacklist: list[str]
    whitelist: list[str]
    worker_count: int


class NewPluginKind(Protocol):
    # mypy docs recommend Protocols to type hint the self parameter of mixin classes
    # (see https://mypy.readthedocs.io/en/latest/more_types.html#mixin-classes)

    @property
    def metadata(self) -> AnalysisPluginV0.MetaData:
        ...