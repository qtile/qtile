import asyncio
import os
import sys

from libqtile import ipc
from libqtile.backend import base
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
        self.eventloop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.eventloop)

        self.qtile = Qtile(kore, config, self.eventloop, no_spawn=no_spawn, state=state)

        if fname is None:
            # Dots might appear in the host part of the display name
            # during remote X sessions. Let's strip the host part first
            display_name = kore.display_name
            display_number = display_name.partition(":")[2]
            if "." not in display_number:
                display_name += ".0"
            fname = ipc.find_sockfile(display_name)

        if os.path.exists(fname):
            os.unlink(fname)
        self.server = ipc.Server(fname, self.qtile.server.call)

    def loop(self) -> None:
        """Run the event loop"""
        try:
            # replace with asyncio.run(...) on Python 3.7+
            self.eventloop.run_until_complete(self.async_loop())
        finally:
            if sys.version_info >= (3, 6):
                self.eventloop.run_until_complete(self.eventloop.shutdown_asyncgens())
            self.eventloop.close()

        self.qtile.maybe_restart()

    async def async_loop(self) -> None:
        async with self.server:
            await self.qtile.async_loop()
