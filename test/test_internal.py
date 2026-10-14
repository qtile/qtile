import pytest

import libqtile.config
from libqtile.config import Click
from libqtile.lazy import lazy
from libqtile.popup import Popup
from test.conftest import BareConfig


class ClickRecorder:
    def __init__(self):
        self.presses = 0
        self.releases = 0

    def press(self, x, y, button):
        self.presses += 1

    def release(self, x, y, button):
        self.releases += 1


class PopupConfig(BareConfig):
    screens = [libqtile.config.Screen()]
    recorders = []

    @staticmethod
    def make_popup1(qtile):
        rec = ClickRecorder()
        p = Popup(qtile, x=0, y=0, width=100, height=100)
        p.win.process_button_click = rec.press
        p.win.process_button_release = rec.release
        p.draw()
        p.place()
        p.unhide()
        PopupConfig.recorders.append(rec)

    @staticmethod
    def make_popup2(qtile):
        rec = ClickRecorder()
        p = Popup(qtile, x=0, y=0, width=100, height=100)

        def on_press(x, y, button):
            rec.press(x, y, button)
            print("pre-kill")
            p.kill()
            print("post-kill")

        p.win.process_button_click = on_press
        p.win.process_button_release = rec.release
        p.draw()
        p.place()
        p.unhide()
        PopupConfig.recorders.append(rec)


class PopupWithBindingConfig(PopupConfig):
    binding_hits = []

    @staticmethod
    def _on_binding(qtile):
        PopupWithBindingConfig.binding_hits.append(1)

    mouse = [Click([], "Button1", lazy.function(_on_binding))]


popup_config = pytest.mark.parametrize("manager", [PopupConfig], indirect=True)
popup_binding_config = pytest.mark.parametrize("manager", [PopupWithBindingConfig], indirect=True)


@popup_config
def test_kill_on_press_over_internal(manager):
    """
    When internal is killed on button press, an underlying window, which may
    subsequently be under the pointer, should not receive release event
    """
    manager.c.eval("self.config.make_popup1(self)")
    manager.c.eval("self.config.make_popup2(self)")

    manager.backend.fake_click(10, 10)

    popup1_presses = manager.c.eval("(self.config.recorders[0].presses)")
    popup1_releases = manager.c.eval("(self.config.recorders[0].releases)")
    popup2_presses = manager.c.eval("(self.config.recorders[1].presses)")
    popup2_releases = manager.c.eval("(self.config.recorders[1].releases)")

    assert popup1_presses == "0"
    assert popup1_releases == "0"
    assert popup2_presses == "1"
    assert popup2_releases == "0"


@popup_binding_config
def test_click_internal_with_binding(manager):
    """Bindings takes precedence over internal window press."""
    manager.c.eval("self.config.make_popup1(self)")

    manager.backend.fake_click(10, 10)

    binding_hits = manager.c.eval("len(self.config.binding_hits)")
    presses = manager.c.eval("self.config.recorders[0].presses")
    releases = manager.c.eval("self.config.recorders[0].releases")

    assert binding_hits == "1"
    assert presses == "0"
    assert releases == "1"
