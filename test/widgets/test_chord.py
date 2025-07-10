# Copyright (c) 2020 Tycho Andersen
# Copyright (c) 2022 elParaguayo
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
import pytest

import libqtile.confreader
from libqtile import hook
from libqtile.config import Key, KeyChord
from libqtile.lazy import lazy
from libqtile.widget import Chord, base
from test.widgets.conftest import FakeBar

RED = "#FF0000"
BLUE = "#00FF00"

textbox = base._TextBox("")
BASE_BACKGROUND = textbox.background
BASE_FOREGROUND = textbox.foreground


def no_op(*args):
    pass


class ChordConf(libqtile.confreader.Config):
    auto_fullscreen = False
    keys = [
        KeyChord([], "a", [Key([], "b", lazy.function(no_op))], mode="persistent_chord"),
        KeyChord(
            [],
            "z",
            [
                Key([], "b", lazy.function(no_op)),
            ],
            name="temporary_name",
        ),
        KeyChord(
            [],
            "y",
            [
                Key([], "b", lazy.function(no_op)),
            ],
            name="mode_true",
            mode=True,
        ),
    ]
    mouse = []
    groups = [libqtile.config.Group("a"), libqtile.config.Group("b")]
    layouts = [libqtile.layout.stack.Stack(num_stacks=1)]
    floating_layout = libqtile.resources.default_config.floating_layout
    screens = [libqtile.config.Screen(top=libqtile.bar.Bar([Chord()], 10))]


chord_config = pytest.mark.parametrize("manager", [ChordConf], indirect=True)


def test_chord_widget(fake_window, fake_qtile):
    chord = Chord(chords_colors={"testcolor": (RED, BLUE)})
    fakebar = FakeBar([chord], window=fake_window)
    chord._configure(fake_qtile, fakebar)

    # Text is blank at start
    assert chord.text == ""

    # Fire hook for testcolor chord
    hook.fire("enter_chord", "testcolor")

    # Chord is in chords_colors so check colours
    assert chord.background == RED
    assert chord.layout.colour == BLUE
    assert chord.text == "testcolor"

    # New chord, not in dictionary so should be default colours
    hook.fire("enter_chord", "test")
    assert chord.text == "test"
    assert chord.background == BASE_BACKGROUND
    assert chord.layout.colour == BASE_FOREGROUND

    # Unnamed chord so no text
    hook.fire("enter_chord", "")
    assert chord.text == ""
    assert chord.background == BASE_BACKGROUND
    assert chord.layout.colour == BASE_FOREGROUND

    # Back into testcolor and custom colours
    hook.fire("enter_chord", "testcolor")
    assert chord.background == RED
    assert chord.layout.colour == BLUE
    assert chord.text == "testcolor"

    # Colours shoud reset when leaving chord
    hook.fire("leave_chord")
    assert chord.text == ""
    assert chord.background == BASE_BACKGROUND
    assert chord.layout.colour == BASE_FOREGROUND

    # Finalize the widget to prevent segfault (the drawer needs to be finalised)
    # We clear the _futures attribute as there are no real timers in it and calls
    # to `cancel()` them will fail.
    chord._futures = []
    chord.finalize()


@chord_config
def test_chord_persistence(manager):
    widget = manager.c.widget["chord"]

    assert widget.info()["text"] == ""

    # Test 1: Test persistent chord mode name
    # Old style where mode contains text.
    # Enter the chord
    manager.c.simulate_keypress([], "a")
    assert widget.info()["text"] == "persistent_chord"

    # Chord has finished but mode should still be in place
    manager.c.simulate_keypress([], "b")
    assert widget.info()["text"] == "persistent_chord"

    # Escape to leave chord
    manager.c.simulate_keypress([], "Escape")
    assert widget.info()["text"] == ""

    # Test 2: Test persistent chord mode name
    # New style - mode = True
    # Enter the chord
    manager.c.simulate_keypress([], "y")
    assert widget.info()["text"] == "mode_true"

    # Chord has finished but mode should still be in place
    manager.c.simulate_keypress([], "b")
    assert widget.info()["text"] == "mode_true"

    # Escape to leave chord
    manager.c.simulate_keypress([], "Escape")
    assert widget.info()["text"] == ""

    # Test 3: Test temporary chord name
    # Enter the chord
    manager.c.simulate_keypress([], "z")
    assert widget.info()["text"] == "temporary_name"

    # Chord has finished and should exit
    manager.c.simulate_keypress([], "b")
    assert widget.info()["text"] == ""

    # Enter the chord
    manager.c.simulate_keypress([], "z")
    assert widget.info()["text"] == "temporary_name"

    # Escape to cancel chord
    manager.c.simulate_keypress([], "Escape")
    assert widget.info()["text"] == ""


def test_chord_mode_name_deprecation(caplog):
    chord = KeyChord([], "a", [Key([], "b", lazy.function(no_op))], mode="persistent_chord")

    assert caplog.records

    log = caplog.records[0]
    assert log.levelname == "WARNING"
    assert "name='persistent_chord'" in log.message

    # Mode should be set to True and name set to the mode name
    assert chord.mode is True
    assert chord.name == "persistent_chord"
