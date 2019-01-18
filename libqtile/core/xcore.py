
import typing

from . import types
from . import xcbq


class XCore(types.Core):
    def get_keys(self) -> typing.List[str]:
        return xcbq.keysyms.keys()

    def get_modifiers(self) -> typing.List[str]:
        return xcbq.ModMasks.keys()
