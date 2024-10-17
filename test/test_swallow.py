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
import pytest

import libqtile
from libqtile import config
from libqtile.backend.x11.core import Core
from libqtile.confreader import Config
from libqtile.lazy import lazy


# Function that increments a counter
@lazy.function
def swallow_inc(qtile):
    qtile.test_data += 1
    return True


# Config with multiple keys and swallow parameters
class SwallowConfig(Config):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        @libqtile.hook.subscribe.startup
        def _():
            libqtile.qtile.test_data = 0

    keys = [
        config.Key(
            ["control"],
            "k",
            swallow_inc(),
        ),
        config.Key(["control"], "j", swallow_inc(), swallow=False),
        config.Key(["control"], "i", swallow_inc().when(layout="idonotexist")),
        config.Key(
            ["control"],
            "o",
            swallow_inc().when(layout="idonotexist"),
            swallow_inc(),
        ),
    ]


# Helper to send process_key_event to the core manager
# It also looks up the keysym and mask to pass to it
def send_process_key_event(manager, key):
    keysym, mask = Core.lookup_key(None, key)
    output = manager.c.eval(f"self.process_key_event({keysym}, {mask})[1]")
    # Assert if eval successful
    assert output[0]
    # Convert the string to a bool
    return output[1] == "True"


def get_test_counter(manager):
    output = manager.c.eval("self.test_data")
    # Assert if eval successful
    assert output[0]
    return int(output[1])


@pytest.mark.parametrize("manager", [SwallowConfig], indirect=True)
def test_swallow(manager):
    # The first key needs to be True as swallowing is not set here
    # We expect the second key to not be handled, as swallow is set to False
    # The third needs to not be swallowed as the layout .when(...) check does not succeed
    # The fourth needs to be True as one of the functions is executed due to passing the .when(...) check
    expectedexecuted = [True, True, False, True]
    expectedswallow = [True, False, False, True]

    # Loop over all the keys in the config and assert
    prev_counter = 0
    for index, key in enumerate(SwallowConfig.keys):
        assert send_process_key_event(manager, key) == expectedswallow[index]

        # Test if the function was executed like we expected
        counter = get_test_counter(manager)
        if expectedexecuted[index]:
            assert counter > prev_counter
        else:
            assert counter == prev_counter
        prev_counter = counter

    not_used_key = config.Key(
        ["control"],
        "h",
        swallow_inc(),
    )

    # This key is not defined in the config so it should not be handled
    assert not send_process_key_event(manager, not_used_key)

    # This key is not defined so test data is not incremented
    assert get_test_counter(manager) == prev_counter
