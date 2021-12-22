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
import pickle
import shutil
import textwrap
from multiprocessing import Value

import pytest

import libqtile.bar
import libqtile.config
import libqtile.layout
from libqtile import config, hook, layout
from libqtile.confreader import Config
from libqtile.ipc import IPCError
from libqtile.lazy import lazy
from libqtile.resources import default_config
from libqtile.widget import TextBox
from test.helpers import TestManager as BareManager


class TwoScreenConfig(Config):
    auto_fullscreen = True
    groups = [config.Group("a"), config.Group("b"), config.Group("c"), config.Group("d")]
    layouts = [layout.stack.Stack(num_stacks=1), layout.stack.Stack(num_stacks=2)]
    floating_layout = default_config.floating_layout
    keys = [
        config.Key(
            ["control"],
            "k",
            lazy.layout.up(),
        ),
        config.Key(
            ["control"],
            "j",
            lazy.layout.down(),
        ),
    ]
    mouse = []
    follow_mouse_focus = False
    reconfigure_screens = False

    screens = []
    fake_screens = [
        libqtile.config.Screen(
            top=libqtile.bar.Bar([TextBox("Qtile Test")], 10), x=0, y=0, width=400, height=600
        ),
        libqtile.config.Screen(
            top=libqtile.bar.Bar([TextBox("Qtile Test")], 10), x=400, y=0, width=400, height=600
        ),
    ]


def test_restart_hook_and_state(manager_nospawn, request, backend, backend_name):

    if backend_name == "wayland":
        pytest.skip("Skipping test on Wayland.")

    manager = manager_nospawn

    # This injection allows us to capture the lifecycle state filepath before
    # restarting Qtile
    inject = textwrap.dedent(
        """
        from libqtile.core.lifecycle import lifecycle

        def no_op(*args, **kwargs):
            pass

        self.lifecycle = lifecycle
        self._do_stop = self._stop
        self._stop = no_op
        """
    )

    # Set up test for restart hook.
    # Use a counter in manager and increment when hook is fired
    def inc_restart_call():
        manager.restart_calls.value += 1

    manager.restart_calls = Value("i", 0)
    hook.subscribe.restart(inc_restart_call)

    manager.start(TwoScreenConfig)

    # Check that hook hasn't been fired yet.
    assert manager.restart_calls.value == 0

    manager.c.group["c"].toscreen(0)
    manager.c.group["d"].toscreen(1)

    manager.test_window("one")
    manager.test_window("two")
    wins = {w["name"]: w["id"] for w in manager.c.windows()}
    manager.c.window[wins["one"]].togroup("c")
    manager.c.window[wins["two"]].togroup("d")

    # Inject the code and start the restart
    manager.c.eval(inject)
    manager.c.restart()

    # Check hook fired
    assert manager.restart_calls.value == 1

    # Get the path to the state file
    _, state_file = manager.c.eval("self.lifecycle.state_file")
    assert state_file

    # We need a copy of this as the next file will probably overwrite it
    original_state = f"{state_file}-original"
    shutil.copy(state_file, original_state)

    # Stop the manager
    manager.c.eval("self._do_stop()")

    # Manager should have shutdown now so trying to access it will raise an error
    with pytest.raises((IPCError, ConnectionResetError)):
        assert manager.c.status()

    # Set up a new manager which takes our state file
    with BareManager(backend, request.config.getoption("--debuglog")) as restarted_manager:
        restarted_manager.start(TwoScreenConfig, state=state_file)

        # Test 1:
        # Check that groups are shown on correct screens
        screen0_info = restarted_manager.c.screen[0].group.info()
        assert screen0_info["name"] == "c"
        assert screen0_info["screen"] == 0

        screen1_info = restarted_manager.c.screen[1].group.info()
        assert screen1_info["name"] == "d"
        assert screen1_info["screen"] == 1

        # Test 2:
        # Check that clients are returned to the correct groups
        assert len(restarted_manager.c.windows()) == 2

        name_to_group = {w["name"]: w["group"] for w in restarted_manager.c.windows()}
        assert name_to_group["one"] == "c"
        assert name_to_group["two"] == "d"

        # Test 3:
        # Check that state file is the same

        # As before, inject code, restart and get state file
        restarted_manager.c.eval(inject)
        restarted_manager.c.restart()
        _, restarted_state = restarted_manager.c.eval("self.lifecycle.state_file")
        assert restarted_state
        restarted_manager.c.eval("self._do_stop()")

    # Load the two QtileState objects
    with open(original_state, "rb") as f:
        original = pickle.load(f)

    with open(restarted_state, "rb") as f:
        restarted = pickle.load(f)

    # Confirm that they're the same
    assert original.groups == restarted.groups
    assert original.screens == restarted.screens
    assert original.current_screen == restarted.current_screen
    assert original.scratchpads == restarted.scratchpads
