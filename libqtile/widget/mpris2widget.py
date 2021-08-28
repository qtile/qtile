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
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from dbus_next import Message, Variant
from dbus_next.constants import MessageType

from libqtile.command.base import expose_command
from libqtile.log_utils import logger
from libqtile.utils import _send_dbus_message, add_signal_receiver
from libqtile.widget import base

if TYPE_CHECKING:
    from typing import Any

MPRIS_PATH = "/org/mpris/MediaPlayer2"
MPRIS_OBJECT = "org.mpris.MediaPlayer2"
MPRIS_PLAYER = "org.mpris.MediaPlayer2.Player"
PROPERTIES_INTERFACE = "org.freedesktop.DBus.Properties"


class Mpris2(base._TextBox):
    """An MPRIS 2 widget

    A widget which displays the current track/artist of your favorite MPRIS
    player. This widget scrolls the text if neccessary and information that
    is displayed is configurable.

    Basic mouse controls are also available: button 1 = play/pause,
    scroll up = next track, scroll down = previous track.

    Widget requirements: dbus-next_.

    .. _dbus-next: https://pypi.org/project/dbus-next/
    """

    defaults = [
        ("name", "audacious", "Name of the MPRIS widget."),
        (
            "objname",
            None,
            "DBUS MPRIS 2 compatible player identifier"
            "- Find it out with dbus-monitor - "
            "Also see: http://specifications.freedesktop.org/"
            "mpris-spec/latest/#Bus-Name-Policy. "
            "``None`` will listen for notifications from all MPRIS2 compatible players.",
        ),
        (
            "display_metadata",
            ["xesam:title", "xesam:album", "xesam:artist"],
            "Which metadata identifiers to display. "
            "See http://www.freedesktop.org/wiki/Specifications/mpris-spec/metadata/#index5h3 "
            "for available values",
        ),
        ("scroll", True, "Whether text should scroll."),
        ("playing_text", "{track}", "Text to show when playing"),
        ("paused_text", "Paused: {track}", "Text to show when paused"),
        ("stopped_text", "", "Text to show when stopped"),
        (
            "stop_pause_text",
            None,
            "(Deprecated) Optional text to display when in the stopped/paused state",
        ),
        (
            "no_metadata_text",
            "No metadata for current track",
            "Text to show when track has no metadata",
        ),
    ]

    def __init__(self, **config):
        base._TextBox.__init__(self, "", **config)
        self.add_defaults(Mpris2.defaults)
        self.is_playing = False
        self.count = 0
        self.displaytext = ""
        self.track_info = ""
        self.status = "{track}"
        self.add_callbacks(
            {
                "Button1": self.play_pause,
                "Button4": self.next,
                "Button5": self.previous,
            }
        )
        paused = ""
        stopped = ""
        if "stop_pause_text" in config:
            logger.warning(
                "The use of 'stop_pause_text' is deprecated. Please use 'paused_text' and 'stopped_text' instead."
            )
            if "paused_text" not in config:
                paused = self.stop_pause_text

            if "stopped_text" not in config:
                stopped = self.stop_pause_text

        self.prefixes = {
            "Playing": self.playing_text,
            "Paused": paused or self.paused_text,
            "Stopped": stopped or self.stopped_text,
        }

        self._current_player: str | None = None
        self.player_names: dict[str, str] = {}

    @property
    def player(self) -> str:
        if self._current_player is None:
            return "None"
        else:
            return self.player_names.get(self._current_player, "Unknown")

    async def _config_async(self):
        subscribe = await add_signal_receiver(
            self.message,
            session_bus=True,
            signal_name="PropertiesChanged",
            bus_name=self.objname,
            path="/org/mpris/MediaPlayer2",
            dbus_interface="org.freedesktop.DBus.Properties",
        )

        if not subscribe:
            logger.warning("Unable to add signal receiver for Mpris2 players")

    def message(self, message):
        if message.message_type != MessageType.SIGNAL:
            return

        asyncio.create_task(self.process_message(message))

    async def process_message(self, message):
        current_player = message.sender

        if current_player not in self.player_names:
            self.player_names[current_player] = await self.get_player_name(current_player)

        self._current_player = current_player

        self.parse_message(*message.body)

    async def get_player_name(self, player):
        bus, message = await _send_dbus_message(
            True,
            MessageType.METHOD_CALL,
            player,
            PROPERTIES_INTERFACE,
            MPRIS_PATH,
            "Get",
            "ss",
            [MPRIS_OBJECT, "Identity"],
        )

        if bus:
            bus.disconnect()

        if message.message_type != MessageType.METHOD_RETURN:
            logger.warning("Could not retrieve identity of player on %s.", player)
            return ""

        return message.body[0].value

    def parse_message(
        self,
        _interface_name: str,
        changed_properties: dict[str, Any],
        _invalidated_properties: list[str],
    ) -> None:
        """
        http://specifications.freedesktop.org/mpris-spec/latest/Track_List_Interface.html#Mapping:Metadata_Map
        """
        if not self.configured:
            return

        if "Metadata" not in changed_properties and "PlaybackStatus" not in changed_properties:
            return

        self.displaytext = ""

        metadata = changed_properties.get("Metadata")
        if metadata:
            self.track_info = self.get_track_info(metadata.value)

        playbackstatus = getattr(changed_properties.get("PlaybackStatus"), "value", None)
        if playbackstatus:
            self.is_playing = playbackstatus == "Playing"
            self.status = self.prefixes.get(playbackstatus, "{track}")

        if not self.track_info:
            self.track_info = self.no_metadata_text

        self.displaytext = self.status.format(track=self.track_info)

        if self.text != self.displaytext:
            self.update(self.displaytext)

    def get_track_info(self, metadata: dict[str, Variant]) -> str:
        meta_list = []
        for key in self.display_metadata:
            val = getattr(metadata.get(key), "value", None)
            if isinstance(val, str):
                meta_list.append(val)
            elif isinstance(val, list):
                val = " - ".join((y for y in val if isinstance(y, str)))
                meta_list.append(val)

        text = " - ".join(meta_list)
        text.replace("\n", "")

        return text

    def _player_cmd(self, cmd: str) -> None:
        if self._current_player is None:
            return

        task = asyncio.create_task(self._send_player_cmd(cmd))
        task.add_done_callback(self._task_callback)

    async def _send_player_cmd(self, cmd: str) -> Message | None:
        bus, message = await _send_dbus_message(
            True,
            MessageType.METHOD_CALL,
            self._current_player,
            MPRIS_PLAYER,
            MPRIS_PATH,
            cmd,
            "",
            [],
        )

        if bus:
            bus.disconnect()

        return message

    def _task_callback(self, task: asyncio.Task) -> None:
        message = task.result()

        # This happens if we can't connect to dbus. Logger call is made
        # elsewhere so we don't need to do any more here.
        if message is None:
            return

        if message.message_type != MessageType.METHOD_RETURN:
            logger.warning("Unable to send command to player.")

    @expose_command()
    def play_pause(self) -> None:
        """Toggle the playback status."""
        self._player_cmd("PlayPause")

    @expose_command()
    def next(self) -> None:
        """Play the next track."""
        self._player_cmd("Next")

    @expose_command()
    def previous(self) -> None:
        """Play the previous track."""
        self._player_cmd("Previous")

    @expose_command()
    def stop(self) -> None:
        """Stop playback."""
        self._player_cmd("Stop")

    @expose_command()
    def info(self):
        """What's the current state of the widget?"""
        d = base._TextBox.info(self)
        d.update(dict(isplaying=self.is_playing, player=self.player))
        return d
