import os
import shutil
import signal
import subprocess

import pytest

import libqtile.config
import libqtile.confreader
import libqtile.layout
from libqtile.bar import Bar
from libqtile.widget.base import ORIENTATION_HORIZONTAL


@pytest.fixture(scope="function")
def fake_bar():
    return FakeBar([])


class FakeBar(Bar):
    def __init__(self, widgets, size=24, width=100, window=None, **config):
        Bar.__init__(self, widgets, size, **config)
        self.height = size
        self.width = width
        self.window = window
        self.horizontal = ORIENTATION_HORIZONTAL

    def draw(self):
        pass


TEST_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(TEST_DIR), "data")


@pytest.fixture(scope="module")
def svg_img_as_pypath():
    "Return the py.path object of a svg image"
    import py

    audio_volume_muted = os.path.join(
        DATA_DIR,
        "svg",
        "audio-volume-muted.svg",
    )
    audio_volume_muted = py.path.local(audio_volume_muted)
    return audio_volume_muted


@pytest.fixture(scope="module")
def fake_qtile():
    import asyncio

    def no_op(*args, **kwargs):
        pass

    class FakeQtile:
        def __init__(self):
            self.register_widget = no_op

        # Widgets call call_soon(asyncio.create_task, self._config_async)
        # at _configure. The coroutine needs to be run in a loop to suppress
        # warnings
        def call_soon(self, func, *args):
            coroutines = [arg for arg in args if asyncio.iscoroutine(arg)]
            if coroutines:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                for func in coroutines:
                    loop.run_until_complete(func)
                loop.close()

    return FakeQtile()


# Fixture that defines a minimal configurations for testing widgets.
# When used in a test, the function needs to receive a list of screens
# (including bar and widgets) as an argument. This config can then be
# passed to the manager to start.
@pytest.fixture(scope="function")
def minimal_conf_noscreen():
    class MinimalConf(libqtile.confreader.Config):
        auto_fullscreen = False
        keys = []
        mouse = []
        groups = [libqtile.config.Group("a"), libqtile.config.Group("b")]
        layouts = [libqtile.layout.stack.Stack(num_stacks=1)]
        floating_layout = libqtile.resources.default_config.floating_layout
        screens = []

    return MinimalConf


@pytest.fixture(scope="function")
def dbus(monkeypatch):
    # for Github CI/Ubuntu, dbus-launch is provided by "dbus-x11" package
    launcher = shutil.which("dbus-launch")

    # If dbus-launch can't be found then tests will fail so we
    # need to skip
    if launcher is None:
        pytest.skip("dbus-launch must be installed")

    # dbus-launch prints two lines which should be set as
    # environmental variables
    result = subprocess.run(launcher, capture_output=True)

    pid = None
    for line in result.stdout.decode().splitlines():

        # dbus server addresses can have multiple "=" so
        # we use partition to split by the first one onle
        var, _, val = line.partition("=")

        # Use monkeypatch to set these variables so they are
        # removed at end of test.
        monkeypatch.setitem(os.environ, var, val)

        # We want the pid so we can kill the process when the
        # test is finished
        if var == "DBUS_SESSION_BUS_PID":
            try:
                pid = int(val)
            except ValueError:
                pass

    # Environment is set and dbus server should be running
    yield

    # Test is over so kill dbus session
    if pid:
        os.kill(pid, signal.SIGTERM)
