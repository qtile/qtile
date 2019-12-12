import os
import typing

from . import base
from . import xcbq
from libqtile.utils import QtileError


class XCore(base.Core):
    def __init__(self, display_name: str = None) -> None:
        """Setup the X11 core backend

        :param display_name:
            The display name to setup the X11 connection to.  Uses the DISPLAY
            environment variable if not given.
        """
        if display_name is None:
            display_name = os.environ.get("DISPLAY")
            if not display_name:
                raise QtileError("No DISPLAY set")

        self.conn = xcbq.Connection(display_name)
        self._display_name = display_name

    @property
    def display_name(self) -> str:
        return self._display_name

    def get_keys(self) -> typing.List[str]:
        return list(xcbq.keysyms.keys())

    def get_modifiers(self) -> typing.List[str]:
        return list(xcbq.ModMasks.keys())
