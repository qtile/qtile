import contextlib
import os
import textwrap

import pytest

from test.helpers import BareConfig, TestManager

try:
    from libqtile.backend.wayland.core import Core

    has_wayland = True
except ImportError:
    has_wayland = False
from test.helpers import Backend

wlr_env = {
    "WLR_BACKENDS": "headless",
    "WLR_LIBINPUT_NO_DEVICES": "1",
    "WLR_RENDERER_ALLOW_SOFTWARE": "1",
    "WLR_RENDERER": "pixman",
    "XDG_RUNTIME_DIR": "/tmp",
}


@contextlib.contextmanager
def wayland_environment(outputs):
    """This backend just needs some environmental variables set"""
    env = wlr_env.copy()
    env["WLR_HEADLESS_OUTPUTS"] = str(outputs)
    yield env


@pytest.fixture(scope="function")
def wmanager(request, wayland_session):
    """
    This replicates the `manager` fixture except that the Wayland backend is hard-coded.
    We cannot parametrize the `backend_name` fixture module-wide because it gets
    parametrized by `pytest_generate_tests` in test/conftest.py and only one of these
    parametrize calls can be used.
    """
    config = getattr(request, "param", BareConfig)
    backend = WaylandBackend(wayland_session)

    with TestManager(backend, request.config.getoption("--debuglog")) as manager:
        manager.start(config)
        yield manager


class WaylandBackend(Backend):
    name = "wayland"

    def __init__(self, env, args=()):
        self.env = env
        self.args = args
        self.core = Core
        self.manager = None

    def create(self):
        """This is used to instantiate the Core"""
        os.environ.update(self.env)
        return self.core(*self.args)

    def configure(self, manager):
        """This backend needs to get WAYLAND_DISPLAY variable."""
        success, display = manager.c.eval("self.core.display_name")
        assert success
        self.env["WAYLAND_DISPLAY"] = display
        _, self.env["DISPLAY"] = manager.c.eval("self.core.xdisplay_name")

    def fake_click(self, x, y):
        """Click at the specified coordinates"""
        # Currently only restacks windows, and does not trigger bindings
        self.manager.c.eval(
            textwrap.dedent(
                f"""
            self.core.warp_pointer({x}, {y})
            self.core._focus_by_click()
        """
            )
        )

    def get_all_windows(self):
        """Get a list of all windows in ascending order of Z position"""
        return self.manager.c.core.query_tree()


def new_xdg_client(wmanager, name="xdg"):
    """Helper to create 'regular' windows in the XDG shell"""
    pid = wmanager.test_window(name)
    wmanager.c.sync()
    return pid


def new_layer_client(wmanager, name="layer"):
    """Helper to create layer shell windows, which are always static"""
    pid = wmanager.test_notification(name)
    wmanager.c.sync()
    return pid
