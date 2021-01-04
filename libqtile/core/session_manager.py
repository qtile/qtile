import asyncio
import os
import tempfile
from typing import Optional

from libqtile import ipc
from libqtile.backend import base
from libqtile.core.lifecycle import lifecycle
from libqtile.core.loop import QtileLoop
from libqtile.core.manager import Qtile


class SessionManager:
    def __init__(
        self, kore: base.Core, config, *, fname: str = None, no_spawn=False, state=None
    ) -> None:
        """Manages a qtile session

        :param kore:
            The core backend to use for the session.
        :param config:
            The configuration to use for the qtile instance.
        :param fname:
            The file name to use as the qtile socket file.
        :param no_spawn:
            If the instance has already been started, then don't re-run the
            startup once hook.
        :param state:
            The state to restart the qtile instance with.
        """
        lifecycle.behavior = lifecycle.behavior.TERMINATE

        self.qtile = Qtile(kore, config, no_spawn=no_spawn, state=state)
        self.server = ipc.Server(
            self._prepare_socket(fname),
            self.qtile.server.call,
        )

    def _prepare_socket(self, fname: Optional[str] = None) -> str:
        if fname is None:
            # Dots might appear in the host part of the display name
            # during remote X sessions. Let's strip the host part first
            display_name = self.qtile.core.display_name
            display_number = display_name.partition(":")[2]
            if "." not in display_number:
                display_name += ".0"
            fname = ipc.find_sockfile(display_name)

        if os.path.exists(fname):
            os.unlink(fname)

        return fname

    def _restart(self):
        lifecycle.behavior = lifecycle.behavior.RESTART
        state_file = os.path.join(tempfile.gettempdir(), 'qtile-state')
        with open(state_file, 'wb') as f:
            self.qtile.dump_state(f)
        lifecycle.state_file = state_file

    def loop(self) -> None:
        try:
            asyncio.run(self.async_loop())
        finally:
            if self.qtile.should_restart:
                self._restart()

    async def async_loop(self) -> None:
        async with QtileLoop(self.qtile), self.server:
            await self.qtile.async_loop()
