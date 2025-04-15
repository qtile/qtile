# Copyright (c) 2024 elParaguayo
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
import asyncio
import json
import shutil

from libqtile.command.base import expose_command
from libqtile.log_utils import logger
from libqtile.utils import create_task
from libqtile.widget.base import _TextBox


class SwayNCReader:
    """
    A class to subscribe and listen to the output of the sway notification centre client.

    Clients can subscribe to the reader and will receive a parsed JSON object whenever a new message
    is received.
    """

    def __init__(self):
        self._swaync = None
        self._finalized = False
        self._process = None
        self.callbacks = []
        self.cmd = None

    def set_path(self, path):
        if self._swaync is not None and path != self._swaync:
            logger.warning("A client is trying to set a different path to swaync. Ignoring.")
            return

        self._swaync = path
        self.cmd = f"{self._swaync} -swb"

    def subscribe(self, callback):
        needs_starting = not self.callbacks
        if callback not in self.callbacks:
            self.callbacks.append(callback)

        if needs_starting:
            create_task(self.run())

    def unsubscribe(self, callback):
        if callback in self.callbacks:
            self.callbacks.remove(callback)

        if not self.callbacks and self._process is not None:
            self.stop()

    async def run(self):
        if self.cmd is None:
            return

        self._process = await asyncio.create_subprocess_shell(
            self.cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )

        while not self._finalized:
            out = await self._process.stdout.readline()
            # process has exited so clear text and exit loop
            if not out:
                self.update("")
                self._process = None
                break
            try:
                message = json.loads(out.decode().strip())
                self.update(message)
            except Exception:
                pass

    def stop(self):
        if self._process is None:
            return

        self._process.terminate()
        self._process = None

    def update(self, msg):
        for callback in self.callbacks:
            callback(msg)


# Create a single instance of the reader.
reader = SwayNCReader()


class SwayNC(_TextBox):
    """
    A simple widget for the Sway Notification Center.

    The widget can display the number of notifications as well as the do not
    disturb status.

    Left-clicking on the widget will toggle the panel. Right-clicking will toggle the
    do not disturb status.
    """

    supported_backends = {"wayland"}

    defaults = [
        ("swaync_client", shutil.which("swaync-client"), "Command to execute."),
        (
            "dnd_status_text",
            ("DND ", ""),
            "Text to show do-not-disturb status. Tuple of text ('on', 'off').",
        ),
        ("format", "{dnd}{num}", "Text to display."),
    ]

    def __init__(self, **config):
        _TextBox.__init__(self, "", **config)
        self.add_defaults(SwayNC.defaults)
        self.add_callbacks({"Button1": self.toggle_panel, "Button3": self.toggle_dnd})

    def _configure(self, qtile, bar):
        _TextBox._configure(self, qtile, bar)
        reader.set_path(self.swaync_client)
        reader.subscribe(self._message_handler)

    def _message_handler(self, msg):
        dnd = self.dnd_status_text[0 if "dnd" in msg.get("class", "") else 1]
        num = msg.get("text", "0")
        self.update(self.format.format(dnd=dnd, num=num))

    @expose_command
    def toggle_panel(self):
        """Show swaync client panel."""
        if self.swaync_client is not None:
            self.qtile.spawn(f"{self.swaync_client} -t -sw")

    @expose_command
    def toggle_dnd(self):
        """Toggle do not disturb status."""
        if self.swaync_client is not None:
            self.qtile.spawn(f"{self.swaync_client} -d -sw")

    def finalize(self):
        reader.unsubscribe(self._message_handler)
        _TextBox.finalize(self)
