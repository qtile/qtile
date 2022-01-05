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
from libqtile.widget import cmus
from test.widgets.conftest import FakeBar


class MockCmusRemoteProcess:
    CalledProcessError = None
    EXTRA = [
        "set aaa_mode all",
        "set continue true",
        "set play_library true",
        "set play_sorted false",
        "set replaygain disabled",
        "set replaygain_limit true",
        "set replaygain_preamp 0.000000",
        "set repeat false",
        "set repeat_current false",
        "set shuffle false",
        "set softvol false",
        "set vol_left 100",
        "set vol_right 100",
    ]

    info = {}
    is_error = False
    index = 0

    @classmethod
    def reset(cls):
        cls.info = [
            [
                "status playing",
                "file /playing/file/rickroll.mp3",
                "duration 222",
                "position 14",
                "tag artist Rick Astley",
                "tag album Whenever You Need Somebody",
                "tag title Never Gonna Give You Up",
            ],
            [
                "status playing",
                "file http://playing/file/sweetcaroline.mp3",
                "duration 222",
                "position 14",
                "tag artist Neil Diamond",
                "tag album Greatest Hits",
                "tag title Sweet Caroline",
            ],
            [
                "status stopped",
                "file http://streaming.source/tomjones.m3u",
                "duration -1",
                "position -9",
                "tag title It's Not Unusual",
                "stream tomjones",
            ],
            [
                "status playing",
                "file /playing/file/always.mp3",
                "duration 222",
                "position 14",
                "tag artist Above & Beyond",
                "tag album Anjunabeats 14",
                "tag title Always - Tinlicker Extended Mix",
            ],
        ]
        cls.index = 0
        cls.is_error = False

    @classmethod
    def call_process(cls, cmd):
        if cls.is_error:
            raise subprocess.CalledProcessError(-1, cmd=cmd, output="Couldn't connect to cmus.")

        if cmd[1:] == ["-C", "status"]:
            track = cls.info[cls.index]
            track.extend(cls.EXTRA)
            output = "\n".join(track)
            return output

        elif cmd[1] == "-p":
            cls.info[cls.index][0] = "status playing"

        elif cmd[1] == "-u":
            if cls.info[cls.index][0] == "status playing":
                cls.info[cls.index][0] = "status paused"

            elif cls.info[cls.index][0] == "status paused":
                cls.info[cls.index][0] = "status playing"

        elif cmd[1] == "-n":
            cls.index = (cls.index + 1) % len(cls.info)

        elif cmd[1] == "-r":
            cls.index = (cls.index - 1) % len(cls.info)

    @classmethod
    def Popen(cls, cmd):  # noqa: N802
        cls.call_process(cmd)


def no_op(*args, **kwargs):
    pass


@pytest.fixture
def patched_cmus(monkeypatch):
    MockCmusRemoteProcess.reset()
    monkeypatch.setattr("libqtile.widget.cmus.subprocess", MockCmusRemoteProcess)
    monkeypatch.setattr(
        "libqtile.widget.cmus.subprocess.CalledProcessError", subprocess.CalledProcessError
    )
    monkeypatch.setattr(
        "libqtile.widget.cmus.base.ThreadPoolText.call_process",
        MockCmusRemoteProcess.call_process,
    )
    return cmus


def test_cmus(fake_qtile, patched_cmus, fake_window):
    widget = patched_cmus.Cmus()
    fakebar = FakeBar([widget], window=fake_window)
    widget._configure(fake_qtile, fakebar)
    text = widget.poll()
    assert text == "♫ Rick Astley - Never Gonna Give You Up"
    assert widget.layout.colour == widget.play_color

    widget.play()
    text = widget.poll()
    assert text == "♫ Rick Astley - Never Gonna Give You Up"
    assert widget.layout.colour == widget.noplay_color


def test_cmus_play_stopped(fake_qtile, patched_cmus, fake_window):
    widget = patched_cmus.Cmus()

    # Set track to a stopped item
    MockCmusRemoteProcess.index = 2
    fakebar = FakeBar([widget], window=fake_window)
    widget._configure(fake_qtile, fakebar)
    text = widget.poll()

    # It's stopped so colour should reflect this
    assert text == "♫ tomjones"
    assert widget.layout.colour == widget.noplay_color

    widget.play()
    text = widget.poll()
    assert text == "♫ tomjones"
    assert widget.layout.colour == widget.play_color


def test_cmus_buttons(minimal_conf_noscreen, manager_nospawn, patched_cmus):
    widget = patched_cmus.Cmus(update_interval=30)
    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=libqtile.bar.Bar([widget], 10))]
    manager_nospawn.start(config)
    topbar = manager_nospawn.c.bar["top"]

    cmuswidget = manager_nospawn.c.widget["cmus"]
    assert cmuswidget.info()["text"] == "♫ Rick Astley - Never Gonna Give You Up"

    # Play next track
    # Non-local file source so widget just displays title
    topbar.fake_button_press(0, "top", 0, 0, button=4)
    cmuswidget.eval("self.update(self.poll())")
    assert cmuswidget.info()["text"] == "♫ Sweet Caroline"

    # Play next track
    # Stream source so widget just displays stream info
    topbar.fake_button_press(0, "top", 0, 0, button=4)
    cmuswidget.eval("self.update(self.poll())")
    assert cmuswidget.info()["text"] == "♫ tomjones"

    # Play previous track
    # Non-local file source so widget just displays title
    topbar.fake_button_press(0, "top", 0, 0, button=5)
    cmuswidget.eval("self.update(self.poll())")
    assert cmuswidget.info()["text"] == "♫ Sweet Caroline"


def test_cmus_error_handling(fake_qtile, patched_cmus, fake_window):
    widget = patched_cmus.Cmus()
    MockCmusRemoteProcess.is_error = True
    fakebar = FakeBar([widget], window=fake_window)
    widget._configure(fake_qtile, fakebar)
    text = widget.poll()

    # Widget does nothing with error message so text is blank
    # TODO: update widget to show error?
    assert text == ""


def test_escape_text(fake_qtile, patched_cmus, fake_window):
    widget = patched_cmus.Cmus()

    # Set track to a stopped item
    MockCmusRemoteProcess.index = 3
    fakebar = FakeBar([widget], window=fake_window)
    widget._configure(fake_qtile, fakebar)
    text = widget.poll()

    # It's stopped so colour should reflect this
    assert text == "♫ Above &amp; Beyond - Always - Tinlicker Extended Mix"
