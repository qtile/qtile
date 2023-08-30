# -*- coding: utf-8 -*-
# Copyright (c) 2023 elParaguayo
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
import pulsectl_asyncio
from pulsectl import PulseError

from libqtile.command.base import expose_command
from libqtile.log_utils import logger
from libqtile.utils import create_task
from libqtile.widget.volume import Volume


class PulseVolume(Volume):
    """
    Volume widget for systems using PulseAudio.

    The widget connects to the PulseAudio server by using the libpulse library
    and so should be updated virtually instantly rather than needing to poll the
    volume status regularly (NB this means that the ``update_interval`` parameter
    serves no purpose for this widget).

    The widget relies on the `pulsectl_asyncio <https://pypi.org/project/pulsectl-asyncio/>`__
    library to access the libpulse bindings.
    """

    defaults = [
        ("limit_max_volume", False, "Limit maximum volume to 100%"),
    ]

    def __init__(self, **config):
        Volume.__init__(self, **config)
        self.add_defaults(PulseVolume.defaults)
        self._subscribed = False
        self._event_handler = None
        self.default_sink = None
        self.default_sink_name = None
        self._previous_state = (-1.0, -1)
        self.pulse = None

    def _configure(self, qtile, bar):
        self.pulse = pulsectl_asyncio.PulseAsync("qtile-pulse")
        Volume._configure(self, qtile, bar)
        if self.theme_path:
            self.setup_images()

    async def _config_async(self):
        # Try to connect to pulse server
        await self._check_pulse_connection()

    async def _check_pulse_connection(self):
        """
        The PulseAsync object subscribes to connection state events so we
        need to check periodically whether the connection has been lost.
        """
        if not self.pulse.connected:
            # Check if we were previously connected to the server and,
            # if so, stop the event handler
            if self._subscribed:
                if self._event_handler is not None:
                    self._event_handler.cancel()
                    self._event_handler = None
                self._subscribed = False
            try:
                await self.pulse.connect()
                logger.debug("Connection to pulseaudio ready")
            except PulseError:
                logger.warning("Failed to connect to pulseaudio, retrying in 10s")
            else:
                # We're connected so get details of the default sink
                await self.get_server_info()

                # Start event listeners for sink and server events
                self._event_handler = create_task(self._event_listener())
                self._subscribed = True

        # Set a timer to check status in 10 seconds time
        self.timeout_add(10, self._check_pulse_connection())

    async def _event_listener(self):
        """Listens for sink and server events from the server."""
        async for event in self.pulse.subscribe_events("sink", "server"):
            # Sink events will signify volume changes
            if event.facility == "sink":
                await self.get_sink_info()
            # Server events include when the default sink changes
            elif event.facility == "server":
                await self.get_server_info()

    async def get_server_info(self):
        info = await self.pulse.server_info()
        self.default_sink_name = info.default_sink_name
        await self.get_sink_info()

    async def get_sink_info(self):
        sinks = [
            sink for sink in await self.pulse.sink_list() if sink.name == self.default_sink_name
        ]
        if not sinks:
            logger.warning("Cold not get info for default sink")
            self.default_sink = None
            return

        self.default_sink = sinks[0]
        self.update()

    async def _change_volume(self, volume):
        """Sets volume on default sink."""
        await self.pulse.volume_set_all_chans(self.default_sink, volume)

    async def _mute(self):
        """Toggles mute status of default sink."""
        await self.pulse.sink_mute(self.default_sink.index, not self.default_sink.mute)

    @expose_command()
    def mute(self):
        """Mute the sound device."""
        create_task(self._mute())

    @expose_command()
    def increase_vol(self, value=None):
        """Increase volume."""
        if not value:
            value = self.default_sink.volume.value_flat + (self.step / 100.0)
        base = self.default_sink.base_volume
        if self.limit_max_volume and value > base:
            value = base

        create_task(self._change_volume(value))

    @expose_command()
    def decrease_vol(self, value=None):
        """Decrease volume."""
        if not value:
            value = self.default_sink.volume.value_flat - (self.step / 100.0)

        value = max(value, 0)

        create_task(self._change_volume(value))

    def update(self):
        """
        same method as in Volume widgets except that here we don't need to
        manually re-schedule update
        """
        if not self.pulse.connected:
            return

        vol = self.get_volume()
        mute = self.default_sink.mute

        if (vol, mute) != self._previous_state:
            self.volume = vol
            # Update the underlying canvas size before actually attempting
            # to figure out how big it is and draw it.
            length = self.length
            self._update_drawer()
            if self.length == length:
                self.draw()
            else:
                self.bar.draw()
            self._previous_state = (vol, mute)

    def get_volume(self):
        if self.default_sink:
            if self.default_sink.mute:
                return -1
            base = self.default_sink.base_volume
            if not base:
                return -1
            current = self.default_sink.volume.value_flat
            return round(current * 100 / base)
        return -1

    def finalize(self):
        # Close the connection to the server
        self.pulse.close()
        Volume.finalize(self)
