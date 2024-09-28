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
                "duration -1",
                "position -9",
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
            [
                "status playing",
                "file /playing/file/always.mp3",
                "duration 222",
                "position 14",
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


@pytest.fixture
def cmus_manager(manager_nospawn, monkeypatch, minimal_conf_noscreen, request):
    widget_config = getattr(request, "param", dict())

    MockCmusRemoteProcess.reset()
    monkeypatch.setattr("libqtile.widget.cmus.subprocess", MockCmusRemoteProcess)
    monkeypatch.setattr(
        "libqtile.widget.cmus.subprocess.CalledProcessError", subprocess.CalledProcessError
    )
    monkeypatch.setattr(
        "libqtile.widget.cmus.base.ThreadPoolText.call_process",
        MockCmusRemoteProcess.call_process,
    )

    config = minimal_conf_noscreen
    config.screens = [
        libqtile.config.Screen(
            top=libqtile.bar.Bar(
                [cmus.Cmus(**widget_config)],
                10,
            ),
        )
    ]

    manager_nospawn.start(config)
    yield manager_nospawn


def test_cmus(cmus_manager):
    widget = cmus_manager.c.widget["cmus"]

    widget.eval("self.update(self.poll())")
    assert widget.info()["text"] == "♫ Rick Astley - Never Gonna Give You Up"
    assert widget.eval("self.layout.colour") == widget.eval("self.playing_color")

    widget.eval("self.play()")
    widget.eval("self.update(self.poll())")
    assert widget.info()["text"] == "♫ Rick Astley - Never Gonna Give You Up"
    assert widget.eval("self.layout.colour") == widget.eval("self.paused_color")


def test_cmus_play_stopped(cmus_manager):
    widget = cmus_manager.c.widget["cmus"]

    # Set track to a stopped item
    widget.eval("subprocess.index = 2")
    widget.eval("self.update(self.poll())")

    # It's stopped so colour should reflect this
    assert widget.info()["text"] == "♫ tomjones"
    assert widget.eval("self.layout.colour") == widget.eval("self.stopped_color")

    widget.eval("self.play()")
    widget.eval("self.update(self.poll())")
    assert widget.info()["text"] == "♫ tomjones"
    assert widget.eval("self.layout.colour") == widget.eval("self.playing_color")


@pytest.mark.parametrize(
    "cmus_manager",
    [{"format": "{position} {duration} {position_percent} {remaining} {remaining_percent}"}],
    indirect=True,
)
def test_cmus_times(cmus_manager):
    widget = cmus_manager.c.widget["cmus"]

    # Check item with valid position and duration
    widget.eval("self.update(self.poll())")

    # Check that times are correct
    assert widget.info()["text"] == "00:14 03:42 6% 03:28 94%"

    # Set track to an item with invalid position and duration
    widget.eval("subprocess.index = 1")
    widget.eval("self.update(self.poll())")

    # Check that times are empty
    assert widget.info()["text"].strip() == ""


def test_cmus_buttons(cmus_manager):
    topbar = cmus_manager.c.bar["top"]

    widget = cmus_manager.c.widget["cmus"]
    assert widget.info()["text"] == "♫ Rick Astley - Never Gonna Give You Up"

    # Play next track
    # Non-local file source
    topbar.fake_button_press(0, 0, button=4)
    widget.eval("self.update(self.poll())")
    assert widget.info()["text"] == "♫ Neil Diamond - Sweet Caroline"

    # Play next track
    # Stream source so widget just displays stream info
    topbar.fake_button_press(0, 0, button=4)
    widget.eval("self.update(self.poll())")
    assert widget.info()["text"] == "♫ tomjones"

    # Play previous track
    # Non-local file source
    topbar.fake_button_press(0, 0, button=5)
    widget.eval("self.update(self.poll())")
    assert widget.info()["text"] == "♫ Neil Diamond - Sweet Caroline"


def test_cmus_error_handling(cmus_manager):
    widget = cmus_manager.c.widget["cmus"]
    widget.eval("subprocess.is_error = True")
    widget.eval("self.update(self.poll())")

    # Widget does nothing with error message so text is blank
    # TODO: update widget to show error?
    assert widget.info()["text"] == ""


def test_escape_text(cmus_manager):
    widget = cmus_manager.c.widget["cmus"]

    # Set track to an item with a title which needs escaping
    widget.eval("subprocess.index = 3")
    widget.eval("self.update(self.poll())")

    # & should be escaped to &amp;
    assert widget.info()["text"] == "♫ Above &amp; Beyond - Always - Tinlicker Extended Mix"


def test_missing_metadata(cmus_manager):
    widget = cmus_manager.c.widget["cmus"]

    # Set track to one that's missing Title and Artist metadata
    widget.eval("subprocess.index = 4")
    widget.eval("self.update(self.poll())")

    # Displayed text should default to the name of the file
    assert widget.info()["text"] == "♫ always.mp3"
