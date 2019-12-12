import asyncio
import os

import libqtile.ipc as ipc
from libqtile.core.manager import Qtile
from libqtile.utils import QtileError


class SessionManager:
    def __init__(
        self,
        kore,
        config,
        *,
        display_name: str = None,
        fname: str = None,
        no_spawn=False,
        state=None
    ) -> None:
        """Manages a qtile session

        :param kore:
            The core backend to use for the session.
        :param config:
            The configuration to use for the qtile instance.
        :param display_name:
            The name of the display to configure.
        :param fname:
            The file name to use as the qtile socket file.
        :param no_spawn:
            If the instance has already been started, then don't re-run the
            startup once hook.
        :param state:
            The state to restart the qtile instance with.
        """
        eventloop = asyncio.new_event_loop()

        if display_name is None:
            display_name = os.environ.get("DISPLAY")
            if not display_name:
                raise QtileError("No DISPLAY set")

        self.qtile = Qtile(
            kore,
            config,
            eventloop,
            display_name=display_name,
            no_spawn=no_spawn,
            state=state,
        )

        if fname is None:
            # Dots might appear in the host part of the display name
            # during remote X sessions. Let's strip the host part first
            display_number = display_name.partition(":")[2]
            if "." not in display_number:
                display_name += ".0"
            fname = ipc.find_sockfile(display_name)

        if os.path.exists(fname):
            os.unlink(fname)
        self.server = ipc.Server(fname, self.qtile.server.call, eventloop)

    def loop(self) -> None:
        """Run the event loop"""
        self.server.start()
        self.qtile.loop()
        self.server.close()
