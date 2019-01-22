
import typing

from . import base
from . import xcbq


class XCore(base.Core):
    def get_keys(self) -> typing.List[str]:
        return list(xcbq.keysyms.keys())

    def get_modifiers(self) -> typing.List[str]:
        return list(xcbq.ModMasks.keys())
