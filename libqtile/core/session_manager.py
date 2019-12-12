import asyncio

from libqtile.core.manager import Qtile


class SessionManager:
    def __init__(self, kore, config, *, display_name=None, fname=None, no_spawn=None, state=None) -> None:
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

        self.qtile = Qtile(
            kore, config, eventloop, display_name=display_name, fname=fname, no_spawn=no_spawn, state=state
        )

    def loop(self) -> None:
        """Run the event loop"""
        self.qtile.loop()
