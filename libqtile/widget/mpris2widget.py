# Copyright (c) 2014 Sebastian Kricner
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 Adi Sieker
# Copyright (c) 2014 Tycho Andersen
# Copyright (c) 2020 elParaguayo
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
from collections import defaultdict
from string import Formatter
from html import escape

from dbus_next import MessageType
from dbus_next.aio import MessageBus

from libqtile.log_utils import logger
from libqtile.utils import add_signal_receiver
from libqtile.widget import base

play_states = {
    'play': '\u23f5',
    'pause': '\u23f8',
}

class Mpris2(base._ScrollText):
    """An MPRIS 2 widget

    A widget which displays the current track/artist of your favorite MPRIS
    player. It should work with all MPRIS 2 compatible players which implement
    a reasonably correct version of MPRIS. This widget scrolls the text if
    necessary and information that is displayed is configurable.
    """

    defaults = [
        ('objname', 'org.mpris.MediaPlayer2.audacious',
            'DBUS MPRIS 2 compatible player identifier'
            '- Find it out with dbus-monitor - '
            'Also see: http://specifications.freedesktop.org/'
            'mpris-spec/latest/#Bus-Name-Policy'),
        ('format', '{play_status}  <b>{title}</b> - {artist}',
            'How to format the status metadata.'
            'Accepted keys are: "play_status" and Xesam properties.'
            'https://www.freedesktop.org/wiki/Specifications/mpris-spec/metadata/'),
        ('play_states', play_states, 'dict of `play_status` strings.'
            'Accepted keys are "play" and "pause".'),
        ('idle_message', '', 'Text to display when the player is idle'),
        ('enable_scrolling', True, 'Wether to scroll the text.'),
    ]

    def __init__(self, **config):
        base._ScrollText.__init__(self, **config)
        self.add_defaults(Mpris2.defaults)

        self.player = None
        self.add_callbacks({
            'Button1': self.send_cmd('play_pause'),
            'Button4': self.send_cmd('next'),
            'Button5': self.send_cmd('previous'),
        })

        self.metadata = {}
        self.play_status = ''
        self.is_playing = None
        self.text = self.idle_message

    async def _config_async(self):
        subscribe = await add_signal_receiver(
            self.message,
            session_bus=True,
            signal_name="PropertiesChanged",
            bus_name=self.objname,
            path="/org/mpris/MediaPlayer2",
            dbus_interface="org.freedesktop.DBus.Properties"
        )

        if not subscribe:
            msg = f"Unable to add signal receiver for {self.objname}."
            logger.warning(msg)

    def message(self, message):
        if message.message_type != MessageType.SIGNAL:
            return

        _, changed_properties, _ = message.body
        self.update_all(changed_properties)

    def update_all(self, changed_properties):
        """https://specifications.freedesktop.org/mpris-spec/latest/Media_Player.html"""
        if not self.configured:
            return

        metadata = changed_properties.get('Metadata')
        if metadata:
            self.update_metadata(metadata.value)

        playbackstatus = changed_properties.get('PlaybackStatus')
        if playbackstatus:
            self.update_playbackstatus(playbackstatus.value)

        self.update_display()

    def update_metadata(self, metadata):
        meta_keys = [
            key for _, key, _, _ in Formatter().parse(self.format)
            if key not in [None, 'play_status']
        ]
        self.metadata = {}
        for key in meta_keys:
            value = getattr(metadata.get(f'xesam:{key}'), 'value', None)
            if isinstance(value, list):
                value = ' & '.join(value)
            self.metadata[key] = value

        if self.markup:
            self.metadata = {
                key: str(escape(value))
                for key, value in self.metadata.items()
            }

    def update_playbackstatus(self, playbackstatus):
        self.is_playing = None
        if playbackstatus == 'Paused':
            self.is_playing = False
            self.play_status = self.play_states['pause']
        elif playbackstatus == 'Playing':
            self.is_playing = True
            self.play_status = self.play_states['play']

    def update_display(self):
        if self.is_playing is None:
            self.text = self.idle_message
        else:
            self.text = self.format.format_map(
                defaultdict(str, play_status=self.play_status, **self.metadata)
            )

        if self.enable_scrolling:
            self.restart_scrolling()
            if not self.is_playing:
                self.pause_scrolling()
        else:
            self.draw()

    def send_cmd(self, command):
        def inner():
            return asyncio.ensure_future(self._send_cmd(command))
        return inner

    async def _send_cmd(self, command):
        if self.player is None:
            await self._init_player()
        await getattr(self.player, 'call_' + command)()

    async def _init_player(self):
        bus = await MessageBus().connect()
        introspection = await bus.introspect(self.objname, '/org/mpris/MediaPlayer2')
        obj = bus.get_proxy_object(self.objname, '/org/mpris/MediaPlayer2', introspection)
        self.player = obj.get_interface('org.mpris.MediaPlayer2.Player')
