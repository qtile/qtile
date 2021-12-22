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

# Widget specific tests

import subprocess

import pytest

import libqtile.config
from libqtile.widget import moc
from test.widgets.conftest import FakeBar


class MockMocpProcess:
    info = {}
    is_error = False
    index = 0

    @classmethod
    def reset(cls):
        cls.info = [
            {
                "State": "PLAY",
                "File": "/playing/file/rickroll.mp3",
                "SongTitle": "Never Gonna Give You Up",
                "Artist": "Rick Astley",
                "Album": "Whenever You Need Somebody",
            },
            {
                "State": "PLAY",
                "File": "/playing/file/sweetcaroline.mp3",
                "SongTitle": "Sweet Caroline",
                "Artist": "Neil Diamond",
                "Album": "Greatest Hits",
            },
            {
                "State": "STOP",
                "File": "/playing/file/itsnotunusual.mp3",
                "SongTitle": "It's Not Unusual",
                "Artist": "Tom Jones",
                "Album": "Along Came Jones",
            },
        ]
        cls.index = 0

    @classmethod
    def run(cls, cmd):
        if cls.is_error:
            raise subprocess.CalledProcessError(-1, cmd=cmd, output="Couldn't connect to moc.")

        arg = cmd[1]

        if arg == "-i":
            output = "\n".join(
                "{k}: {v}".format(k=k, v=v) for k, v in cls.info[cls.index].items()
            )
            return output

        elif arg == "-p":
            cls.info[cls.index]["State"] = "PLAY"

        elif arg == "-G":
            if cls.info[cls.index]["State"] == "PLAY":
                cls.info[cls.index]["State"] = "PAUSE"

            elif cls.info[cls.index]["State"] == "PAUSE":
                cls.info[cls.index]["State"] = "PLAY"

        elif arg == "-f":
            cls.index = (cls.index + 1) % len(cls.info)

        elif arg == "-r":
            cls.index = (cls.index - 1) % len(cls.info)


def no_op(*args, **kwargs):
    pass


@pytest.fixture
def patched_moc(fake_qtile, monkeypatch, fake_window):
    widget = moc.Moc()
    MockMocpProcess.reset()
    monkeypatch.setattr(widget, "call_process", MockMocpProcess.run)
    monkeypatch.setattr("libqtile.widget.moc.subprocess.Popen", MockMocpProcess.run)
    fakebar = FakeBar([widget], window=fake_window)
    widget._configure(fake_qtile, fakebar)
    return widget


def test_moc_poll_string_formatting(patched_moc):

    # Both artist and song title
    assert patched_moc.poll() == "♫ Rick Astley - Never Gonna Give You Up"

    # No artist
    MockMocpProcess.info[0]["Artist"] = ""
    assert patched_moc.poll() == "♫ Never Gonna Give You Up"

    # No title
    MockMocpProcess.info[0]["SongTitle"] = ""
    assert patched_moc.poll() == "♫ rickroll"


def test_moc_state_and_colours(patched_moc):

    # Initial poll - playing
    patched_moc.poll()
    assert patched_moc.layout.colour == patched_moc.play_color

    # Toggle pause
    patched_moc.play()
    patched_moc.poll()
    assert patched_moc.layout.colour == patched_moc.noplay_color

    # Toggle pause --> playing again
    patched_moc.play()
    patched_moc.poll()
    assert patched_moc.layout.colour == patched_moc.play_color


def test_moc_button_presses(manager_nospawn, minimal_conf_noscreen, monkeypatch):

    # This needs to be patched before initialising the widgets as mouse callbacks
    # bind subprocess.Popen.
    monkeypatch.setattr("subprocess.Popen", MockMocpProcess.run)

    # Long interval as we don't need this polling on its own.
    mocwidget = moc.Moc(update_interval=30)
    MockMocpProcess.reset()
    monkeypatch.setattr(mocwidget, "call_process", MockMocpProcess.run)
    monkeypatch.setattr("libqtile.widget.moc.subprocess.Popen", MockMocpProcess.run)

    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=libqtile.bar.Bar([mocwidget], 10))]

    manager_nospawn.start(config)

    # When started, we have the first item playing
    topbar = manager_nospawn.c.bar["top"]
    info = manager_nospawn.c.widget["moc"].info
    assert info()["text"] == "♫ Rick Astley - Never Gonna Give You Up"

    # Trigger next item and wait for update poll
    topbar.fake_button_press(0, "top", 0, 0, button=4)
    manager_nospawn.c.widget["moc"].eval("self.update(self.poll())")
    assert info()["text"] == "♫ Neil Diamond - Sweet Caroline"

    # Trigger next item and wait for update poll
    # This item's state is set to "STOP" so there's no track title
    topbar.fake_button_press(0, "top", 0, 0, button=4)
    manager_nospawn.c.widget["moc"].eval("self.update(self.poll())")
    assert info()["text"] == "♫"

    # Click to play it and get the information
    topbar.fake_button_press(0, "top", 0, 0, button=1)
    manager_nospawn.c.widget["moc"].eval("self.update(self.poll())")
    assert info()["text"] == "♫ Tom Jones - It's Not Unusual"

    # Trigger previous item and wait for update poll
    topbar.fake_button_press(0, "top", 0, 0, button=5)
    manager_nospawn.c.widget["moc"].eval("self.update(self.poll())")
    assert info()["text"] == "♫ Neil Diamond - Sweet Caroline"


def test_moc_error_handling(patched_moc):
    MockMocpProcess.is_error = True
    # Widget does nothing with error message so text is blank
    assert patched_moc.poll() == ""
