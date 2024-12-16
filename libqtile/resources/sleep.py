# Copyright (c) 2022-23, elParaguayo. All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
from __future__ import annotations

import fcntl
import os

from libqtile import hook
from libqtile.log_utils import logger
from libqtile.utils import create_task

try:
    from dbus_next.aio import MessageBus
    from dbus_next.constants import BusType
    from dbus_next.errors import DBusError

    has_dbus = True
except ImportError:
    has_dbus = False

LOGIND_SERVICE = "org.freedesktop.login1"
LOGIND_INTERFACE = LOGIND_SERVICE + ".Manager"
LOGIND_PATH = "/org/freedesktop/login1"


class Inhibitor:
    """
    Class definition to access systemd's login1 service on dbus.

    Listens for `PrepareForSleep` signals and fires appropriate hooks
    when the signal is received.

    Can also set a sleep inhibitor which will be run after the "suspend"
    hook has been fired. This helps hooked functions to complete before
    the system goes to sleep. However, the inhibitor is set to only delay
    sleep, not block it.
    """

    def __init__(self) -> None:
        self.bus: MessageBus | None = None
        self.sleep = False
        self.resume = False
        self.fd: int = -1

    def want_sleep(self) -> None:
        """
        Convenience method to set flag to show we want to know when the
        system is going down for sleep.
        """
        if not has_dbus:
            logger.warning("dbus-next must be installed to listen to sleep signals")
        self.sleep = True

    def want_resume(self) -> None:
        """
        Convenience method to set flag to show we want to know when the
        system is waking from sleep.
        """
        if not has_dbus:
            logger.warning("dbus-next must be installed to listen to resume signals")
        self.resume = True

    def start(self) -> None:
        """
        Will create connection to dbus only if we want to listen out
        for a sleep or wake signal.
        """
        if not has_dbus:
            return

        if not (self.sleep or self.resume):
            return

        create_task(self._start())

    async def _start(self) -> None:
        """
        Creates the bus connection and connects to the org.freedesktop.login1.Manager
        interface. Starts an inhibitor if we are listening for sleep events.
        Attaches handler to the "PrepareForSleep" signal.
        """
        # Connect to bus and Manager interface
        try:
            self.bus = await MessageBus(bus_type=BusType.SYSTEM, negotiate_unix_fd=True).connect()
        except FileNotFoundError:
            self.bus = None
            logger.warning(
                "Could not find logind service. Suspend and resume hooks will be unavailable."
            )
            return

        try:
            introspection = await self.bus.introspect(LOGIND_SERVICE, LOGIND_PATH)
        except DBusError:
            logger.warning(
                "Could not find logind service. Suspend and resume hooks will be unavailable."
            )
            self.bus.disconnect()
            self.bus = None
            return

        obj = self.bus.get_proxy_object(LOGIND_SERVICE, LOGIND_PATH, introspection)
        self.login = obj.get_interface(LOGIND_INTERFACE)

        # If we want to know when the system is sleeping when we request an inhibitor
        if self.sleep:
            self.take()

        # Finally, attach a handler for the "PrepareForSleep" signal
        self.login.on_prepare_for_sleep(self.prepare_for_sleep)

    def take(self) -> None:
        """Create an inhibitor."""
        # Shouldn't happen but, if we already have an inhibitor in place,
        # close it before requesting a new one
        if self.fd > 0:
            self.release()

        # Check that inhibitor was released
        if self.fd < 0:
            create_task(self._take())

    async def _take(self) -> None:
        """Sends the request to dbus to create an inhibitor."""
        # The "Inhibit" method returns a file descriptor
        self.fd = await self.login.call_inhibit(
            "sleep",  # what: The lock type. We only want to inhibit sleep
            "qtile",  # who: Name of program requesting inhibitor
            "Run hooked functions before suspend",  # why: Short description of purpose
            "delay",  # mode: "delay" or "block"
        )

        # We need to set CLOEXEC flag for the file descriptor
        # See: https://github.com/qtile/qtile/pull/4388#issuecomment-1675410090
        # for explanation
        flags = fcntl.fcntl(self.fd, fcntl.F_GETFD)
        fcntl.fcntl(self.fd, fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)

    def release(self) -> None:
        """Closes the file descriptor to release the inhibitor."""
        if self.fd > 0:
            os.close(self.fd)
        else:
            logger.warning("No inhibitor available to release.")

        try:
            os.fstat(self.fd)
        except OSError:
            # File descriptor was successfully closed
            self.fd = -1
        else:
            # We could read the file descriptor so it's still open
            logger.warning("Unable to release inhibitor.")

    def prepare_for_sleep(self, start: bool) -> None:
        """
        Handler for "PrepareForSleep" signal.

        Value of "sleep" is:
        - True when the machine is about to sleep
        - False when the event is over i.e. the machine has woken up
        """
        if start:
            hook.fire("suspend")

            # Note: lock is released after the "suspend" hook has been fired
            # Hooked functions should therefore be synchronous to ensure they
            # complete before the inhbitor is released.
            self.release()
        else:
            # If we're listening for suspend events, we need to request a new
            # inhibitor
            if self.sleep:
                self.take()
            hook.fire("resume")

    def stop(self) -> None:
        """
        Deactivates the inhibitor, removing lock and signal handler
        before closing bus connection.
        """
        if not has_dbus or self.bus is None:
            return

        if self.fd > 0:
            self.release()

        if self.sleep or self.resume:
            self.login.off_prepare_for_sleep(self.prepare_for_sleep)

        self.bus.disconnect()
        self.bus = None


inhibitor = Inhibitor()
