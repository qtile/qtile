# Copyright (c) 2021 elParaguayo
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
import sys
from types import ModuleType

import pytest

import libqtile.config
from libqtile import widget


class MockMPD(ModuleType):
    class ConnectionError(Exception):
        pass

    class CommandError(Exception):
        pass

    class MPDClient:
        tracks = [
            {"title": "Never gonna give you up", "artist": "Rick Astley"},
            {"title": "Sweet Caroline", "artist": "Neil Diamond"},
            {"title": "Marea", "artist": "Fred Again.."},
            {},
        ]

        def __init__(self):
            self._index = 0
            self._connected = False
            self._state_override = True
            self._status = {"state": "pause"}

        @property
        def _current_song(self):
            return self.tracks[self._index]

        def ping(self):
            if not self._connected:
                raise ConnectionError()
            return self._state_override

        def connect(self, host, port):
            return True

        def command_list_ok_begin(self):
            pass

        def status(self):
            return self._status

        def currentsong(self):
            pass

        def command_list_end(self):
            return (self.status(), self._current_song)

        def close(self):
            pass

        def disconnect(self):
            pass

        def pause(self):
            self._status["state"] = "pause"

        def play(self):
            print("PLAYING")
            self._status["state"] = "play"

        def stop(self):
            self._status["state"] = "stop"

        def next(self):
            self._index = (self._index + 1) % len(self.tracks)

        def previous(self):
            self._index = (self._index - 1) % len(self.tracks)

        def add_states(self):
            self._status.update(
                {"repeat": "1", "random": "1", "single": "1", "consume": "1", "updating_db": "1"}
            )

        def force_idle(self):
            self._status["state"] = "stop"
            self._index = 3


@pytest.fixture
def mpd2_manager(manager_nospawn, monkeypatch, minimal_conf_noscreen):
    # monkeypatch.setattr("libqtile.widget.mpd2widget.MPDClient", MockMPDClient)
    monkeypatch.setitem(sys.modules, "mpd", MockMPD("mpd"))

    config = minimal_conf_noscreen
    config.screens = [
        libqtile.config.Screen(
            top=libqtile.bar.Bar(
                [widget.Mpd2()],
                50,
            ),
        )
    ]

    manager_nospawn.start(config)
    yield manager_nospawn


def test_mpd2_widget_display_and_actions(mpd2_manager):
    widget = mpd2_manager.c.widget["mpd2"]
    assert widget.info()["text"] == "⏸ Rick Astley/Never gonna give you up [-----]"

    # Button 1 toggles state
    mpd2_manager.c.bar["top"].fake_button_press(0, "top", 0, 0, 1)
    widget.eval("self.update(self.poll())")
    assert widget.info()["text"] == "▶ Rick Astley/Never gonna give you up [-----]"

    # Button 3 stops
    mpd2_manager.c.bar["top"].fake_button_press(0, "top", 0, 0, 3)
    widget.eval("self.update(self.poll())")
    assert widget.info()["text"] == "■ Rick Astley/Never gonna give you up [-----]"

    # Button 1 toggles state
    mpd2_manager.c.bar["top"].fake_button_press(0, "top", 0, 0, 1)
    widget.eval("self.update(self.poll())")
    assert widget.info()["text"] == "▶ Rick Astley/Never gonna give you up [-----]"

    mpd2_manager.c.bar["top"].fake_button_press(0, "top", 0, 0, 1)
    widget.eval("self.update(self.poll())")
    assert widget.info()["text"] == "⏸ Rick Astley/Never gonna give you up [-----]"

    # Button 5 is "next"
    mpd2_manager.c.bar["top"].fake_button_press(0, "top", 0, 0, 5)
    widget.eval("self.update(self.poll())")
    assert widget.info()["text"] == "⏸ Neil Diamond/Sweet Caroline [-----]"

    mpd2_manager.c.bar["top"].fake_button_press(0, "top", 0, 0, 5)
    widget.eval("self.update(self.poll())")
    assert widget.info()["text"] == "⏸ Fred Again../Marea [-----]"

    # Button 4 is previous
    mpd2_manager.c.bar["top"].fake_button_press(0, "top", 0, 0, 4)
    widget.eval("self.update(self.poll())")
    assert widget.info()["text"] == "⏸ Neil Diamond/Sweet Caroline [-----]"

    mpd2_manager.c.bar["top"].fake_button_press(0, "top", 0, 0, 4)
    widget.eval("self.update(self.poll())")
    assert widget.info()["text"] == "⏸ Rick Astley/Never gonna give you up [-----]"


def test_mpd2_widget_extra_info(mpd2_manager):
    """Quick test to check extra info is displayed ok."""
    widget = mpd2_manager.c.widget["mpd2"]

    # Inject everything to make test quicker
    widget.eval("self.client.add_states()")

    # Update widget and check text
    widget.eval("self.update(self.poll())")
    assert widget.info()["text"] == "⏸ Rick Astley/Never gonna give you up [rz1cU]"


def test_mpd2_widget_idle_message(mpd2_manager):
    """Quick test to check idle message."""
    widget = mpd2_manager.c.widget["mpd2"]

    # Inject everything to make test quicker
    widget.eval("self.client.force_idle()")

    # Update widget and check text
    widget.eval("self.update(self.poll())")
    assert widget.info()["text"] == "■ MPD IDLE[-----]"
