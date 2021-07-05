import contextlib
import os
import textwrap

from libqtile.backend.wayland.core import Core
from test.helpers import Backend

wlr_env = {
    "WLR_BACKENDS": "headless",
    "WLR_LIBINPUT_NO_DEVICES": "1",
    "WLR_RENDERER_ALLOW_SOFTWARE": "1",
    "WLR_RENDERER": "pixman",
}


@contextlib.contextmanager
def wayland_environment(outputs):
    """This backend just needs some environmental variables set"""
    env = wlr_env.copy()
    env["WLR_HEADLESS_OUTPUTS"] = str(outputs)
    yield env


class WaylandBackend(Backend):
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

    def fake_click(self, x, y):
        """Click at the specified coordinates"""
        self.manager.c.eval(textwrap.dedent("""
            self.core._focus_by_click()
            self.core._process_cursor_button(1, True)
        """))

    def get_all_windows(self):
        """Get a list of all windows in ascending order of Z position"""
        success, result = self.manager.c.eval(textwrap.dedent("""
            [win.wid for win in self.core.mapped_windows]
        """))
        assert success
        return eval(result)
