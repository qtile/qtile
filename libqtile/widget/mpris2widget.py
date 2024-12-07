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
import re
import string
from typing import TYPE_CHECKING

from dbus_fast import Message, Variant
from dbus_fast.aio import MessageBus
from dbus_fast.constants import MessageType

from libqtile import pangocffi
from libqtile.command.base import expose_command
from libqtile.log_utils import logger
from libqtile.utils import _send_dbus_message, add_signal_receiver, create_task
from libqtile.widget import base

if TYPE_CHECKING:
    from typing import Any

MPRIS_PATH = "/org/mpris/MediaPlayer2"
MPRIS_OBJECT = "org.mpris.MediaPlayer2"
MPRIS_PLAYER = "org.mpris.MediaPlayer2.Player"
PROPERTIES_INTERFACE = "org.freedesktop.DBus.Properties"
MPRIS_REGEX = re.compile(r"(\{(.*?):(.*?)(:.*?)?\})")


class Mpris2Formatter(string.Formatter):
    """
    Custom string formatter for MPRIS2 metadata.

    Keys have a colon (e.g. "xesam:title") which causes issues with python's string
    formatting as the colon splits the identifier from the format specification.

    This formatter handles this issue by changing the first colon to an underscore and
    then formatting the incoming kwargs to match.

    Additionally, a default value is returned when an identifier is not provided by the
    kwarg data.
    """

    def __init__(self, default=""):
        string.Formatter.__init__(self)
        self._default = default

    def get_value(self, key, args, kwargs):
        """
        Replaces colon in kwarg keys with an underscore before getting value.

        Missing identifiers are replaced with the default value.
        """
        kwargs = {k.replace(":", "_"): v for k, v in kwargs.items()}
        try:
            return pangocffi.markup_escape_text(
                string.Formatter.get_value(self, key, args, kwargs)
            )
        except (IndexError, KeyError):
            return self._default

    def parse(self, format_string):
        """
        Replaces first colon in format string with an underscore.

        This will cause issues if any identifier is provided that does not
        contain a colon. This should not happen according to the MPRIS2
        specification!
        """
        format_string = MPRIS_REGEX.sub(r"{\2_\3\4}", format_string)
        return string.Formatter.parse(self, format_string)


class Mpris2(base._TextBox):
    """An MPRIS 2 widget

    A widget which displays the current track/artist of your favorite MPRIS
    player. This widget scrolls the text if neccessary and information that
    is displayed is configurable.

    The widget relies on players broadcasting signals when the metadata or playback
    status changes. If you are getting inconsistent results then you can enable background
    polling of the player by setting the `poll_interval` parameter. This is disabled by
    default.

    Basic mouse controls are also available: button 1 = play/pause,
    scroll up = next track, scroll down = previous track.

    Widget requirements: dbus-fast_.

    .. _dbus-fast: https://pypi.org/project/dbus-fast/
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
            "format",
            "{xesam:title} - {xesam:album} - {xesam:artist}",
            "Format string for displaying metadata. "
            "See http://www.freedesktop.org/wiki/Specifications/mpris-spec/metadata/#index5h3 "
            "for available values. The special filed '{qtile:player}' can be used to display the "
            "player name.",
        ),
        ("separator", ", ", "Separator for metadata fields that are a list."),
        (
            "display_metadata",
            ["xesam:title", "xesam:album", "xesam:artist"],
            "(Deprecated) Which metadata identifiers to display. ",
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
        (
            "poll_interval",
            0,
            "Periodic background polling interval of player (0 to disable polling).",
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

        if "display_metadata" in config:
            logger.warning(
                "The use of `display_metadata is deprecated. Please use `format` instead."
            )
            self.format = " - ".join(f"{{{s}}}" for s in config["display_metadata"])

        self._formatter = Mpris2Formatter()

        self.prefixes = {
            "Playing": self.playing_text,
            "Paused": paused or self.paused_text,
            "Stopped": stopped or self.stopped_text,
        }

        self._current_player: str | None = None
        self.player_names: dict[str, str] = {}
        self._background_poll: asyncio.TimerHandle | None = None
        self.bus: MessageBus | None = None

    @property
    def player(self) -> str:
        if self._current_player is None:
            return "None"
        else:
            return self.player_names.get(self._current_player, "Unknown")

    async def _config_async(self):
        # These two listeners create separate bus connections. Each connection only has one
        # callback so we don't need any logic to identify the message and the appropriate
        # handler in this code.

        # Set up a listener for NameOwner changes so we can remove players when they close
        await add_signal_receiver(
            self._name_owner_changed,
            session_bus=True,
            signal_name="NameOwnerChanged",
            dbus_interface="org.freedesktop.DBus",
        )

        # Listen out for signals from any Mpris2 compatible player
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

        # If the user has specified a player to be monitored, we can poll it now.
        if self.objname is not None:
            await self._check_player()

    def _name_owner_changed(self, message):
        # We need to track when an interface has been removed from the bus
        # We use the NameOwnerChanged signal and check if the new owner is
        # empty.
        name, _, new_owner = message.body

        # Check if the current player has closed
        if new_owner == "" and name == self._current_player:
            self._current_player = None
            self.update("")

            # Cancel any scheduled background poll
            self._set_background_poll(False)

    def message(self, message):
        create_task(self.process_message(message))

    async def process_message(self, message):
        current_player = message.sender

        if current_player not in self.player_names:
            self.player_names[current_player] = await self.get_player_name(current_player)

        self._current_player = current_player

        self.parse_message(*message.body)

    async def _send_message(self, destination, interface, path, member, signature, body):
        bus, message = await _send_dbus_message(
            session_bus=True,
            message_type=MessageType.METHOD_CALL,
            destination=destination,
            interface=interface,
            path=path,
            member=member,
            signature=signature,
            body=body,
            bus=self.bus,
        )

        # We should reuse the same bus connection for repeated calls.
        if self.bus is None:
            self.bus = bus

        return message

    async def _check_player(self):
        """Check for player at startup and retrieve metadata."""
        if not (self.objname or self._current_player):
            return

        message = await self._send_message(
            self.objname if self.objname else self._current_player,
            PROPERTIES_INTERFACE,
            MPRIS_PATH,
            "GetAll",
            "s",
            [MPRIS_PLAYER],
        )

        # If we get an error here it will be because the player object doesn't exist
        if message.message_type != MessageType.METHOD_RETURN:
            self._current_player = None
            self.update("")
            return

        if message.body:
            self._current_player = message.sender
            self.parse_message(self.objname, message.body[0], [])

    def _set_background_poll(self, poll=True):
        if self._background_poll is not None:
            self._background_poll.cancel()

        if poll:
            self._background_poll = self.timeout_add(self.poll_interval, self._check_player)

    async def get_player_name(self, player):
        message = await self._send_message(
            player,
            PROPERTIES_INTERFACE,
            MPRIS_PATH,
            "Get",
            "ss",
            [MPRIS_OBJECT, "Identity"],
        )

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

        if self.poll_interval:
            self._set_background_poll()

    def get_track_info(self, metadata: dict[str, Variant]) -> str:
        self.metadata = {}
        for key in metadata:
            new_key = key
            val = getattr(metadata.get(key), "value", None)
            if isinstance(val, str):
                self.metadata[new_key] = val
            elif isinstance(val, list):
                self.metadata[new_key] = self.separator.join(y for y in val if isinstance(y, str))
        if self.player is not None:
            self.metadata["qtile:player"] = self.player

        return self._formatter.format(self.format, **self.metadata).replace("\n", "")

    def _player_cmd(self, cmd: str) -> None:
        if self._current_player is None:
            return

        task = create_task(self._send_player_cmd(cmd))
        assert task
        task.add_done_callback(self._task_callback)

    async def _send_player_cmd(self, cmd: str) -> Message | None:
        message = await self._send_message(
            self._current_player,
            MPRIS_PLAYER,
            MPRIS_PATH,
            cmd,
            "",
            [],
        )

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
