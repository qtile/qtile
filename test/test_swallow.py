# Copyright (c) 2021 Jeroen Wijenbergh
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
from libqtile import config
from libqtile.backend.x11 import xcbq
from libqtile.backend.x11.core import Core
from libqtile.confreader import Config
from libqtile.lazy import lazy


# Function that does nothing
def swallow_nop(qtile):
    pass


# Config with multiple keys and swallow parameters
class SwallowConfig(Config):
    keys = [
        config.Key(
            ["control"],
            "k",
            lazy.function(swallow_nop),
        ),
        config.Key(
            ["control"],
            "j",
            lazy.function(swallow_nop),
            swallow=False
        ),
        config.Key(
            ["control"],
            "i",
            lazy.function(swallow_nop).when(layout='idonotexist')
        ),
        config.Key(
            ["control"],
            "o",
            lazy.function(swallow_nop).when(layout='idonotexist'),
            lazy.function(swallow_nop)
        ),
    ]

    mouse = [
        config.Click(
            [],
            "Button1",
            lazy.function(swallow_nop),
        ),
        config.Click(
            ["control"],
            "Button3",
            lazy.function(swallow_nop),
            swallow=False
        ),
        config.Click(
            ["mod4"],
            "Button3",
            lazy.function(swallow_nop).when(layout='idonotexist')
        ),
        config.Click(
            [],
            "Button3",
            lazy.function(swallow_nop).when(layout='idonotexist'),
            lazy.function(swallow_nop)
        ),
    ]


# Helper to send process_key_event to the core manager
# It also looks up the keysym and mask to pass to it
def send_process_key_event(manager, key):
    keysym, mask = Core.lookup_key(None, key)
    output = manager.c.eval(f"self.process_key_event({keysym}, {mask})")
    # Assert if eval successful
    assert output[0]
    # Convert the string to a bool
    return output[1] == 'True'


# Helper to send process_button_click to the core manager
# It also looks up the button code and mask to pass to it
def send_process_button_click(manager, mouse):
    modmask = xcbq.translate_masks(mouse.modifiers)
    output = manager.c.eval(f"self.process_button_click({mouse.button_code}, {modmask}, {0}, {0})")
    # Assert if eval successful
    assert output[0]
    # Convert the string to a bool
    return output[1] == 'True'


def test_swallow(manager_nospawn):
    manager = manager_nospawn
    manager.start(SwallowConfig)

    # The first key needs to be True as swallowing is not set here
    # We expect the second key to not be handled, as swallow is set to False
    # The third needs to not be swallowed as the layout .when(...) check does not succeed
    # The fourth needs to be True as one of the functions is executed due to passing the .when(...) check
    expectedswallow = [True, False, False, True]

    # Loop over all the keys in the config and assert
    for index, key in enumerate(SwallowConfig.keys):
        assert send_process_key_event(manager, key) == expectedswallow[index]

    # Loop over all the mouse bindings in the config and assert
    for index, binding in enumerate(SwallowConfig.mouse):
        assert send_process_button_click(manager, binding) == expectedswallow[index]

    not_used_key = config.Key(
        ["control"],
        "h",
        lazy.function(swallow_nop),
    )

    not_used_mouse = config.Click(
        [],
        "Button2",
        lazy.function(swallow_nop),
    )

    # This key is not defined in the config so it should not be handled
    assert not send_process_key_event(manager, not_used_key)

    # This mouse binding is not defined in the config so it should not be handled
    assert not send_process_button_click(manager, not_used_mouse)
