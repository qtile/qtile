from pathlib import Path

import pytest

from libqtile import config, confreader, utils
from libqtile.backend.base.core import Output
from libqtile.bar import Bar
from libqtile.config import Screen, ScreenRect
from libqtile.widget import TextBox

configs_dir = Path(__file__).resolve().parent / "configs"


def load_config(name):
    f = confreader.Config(configs_dir / name)
    f.load()
    return f


def test_validate():
    # bad key
    f = load_config("basic.py")
    f.keys[0].key = "nonexistent"
    with pytest.raises(confreader.ConfigError):
        f.validate()

    # bad modifier
    f = load_config("basic.py")
    f.keys[0].modifiers = ["nonexistent"]
    with pytest.raises(confreader.ConfigError):
        f.validate()


def test_basic():
    f = load_config("basic.py")
    assert f.keys


def test_syntaxerr():
    with pytest.raises(SyntaxError):
        load_config("syntaxerr.py")


def test_falls_back():
    f = load_config("basic.py")
    # We just care that it has a default, we don't actually care what the
    # default is; don't assert anything at all about the default in case
    # someone changes it down the road.
    assert hasattr(f, "follow_mouse_focus")


def cmd(x):
    return None


def test_ezkey():
    key = config.EzKey("M-A-S-a", cmd, cmd)
    modkey, altkey = (config.EzConfig.modifier_keys[i] for i in "MA")
    assert key.modifiers == [modkey, altkey, "shift"]
    assert key.key == "a"
    assert key.commands == (cmd, cmd)

    key = config.EzKey("M-<Tab>", cmd)
    assert key.modifiers == [modkey]
    assert key.key == "Tab"
    assert key.commands == (cmd,)

    with pytest.raises(utils.QtileError):
        config.EzKey("M--", cmd)

    with pytest.raises(utils.QtileError):
        config.EzKey("Z-Z-z", cmd)

    with pytest.raises(utils.QtileError):
        config.EzKey("asdf", cmd)

    with pytest.raises(utils.QtileError):
        config.EzKey("M-a-A", cmd)


def test_ezclick_ezdrag():
    btn = config.EzClick("M-1", cmd)
    assert btn.button == "Button1"
    assert btn.modifiers == [config.EzClick.modifier_keys["M"]]

    btn = config.EzDrag("A-2", cmd)
    assert btn.button == "Button2"
    assert btn.modifiers == [config.EzClick.modifier_keys["A"]]


def test_screen_underbar_methods():
    one = config.Screen(x=10, y=10, width=10, height=10)
    two = config.Screen(x=20, y=20, width=20, height=20)

    assert hash(one) != hash(two)
    assert hash(one) == hash(one)
    assert one != two
    assert one == one


def test_screen_serial_ordering_the_order(manager_nospawn, minimal_conf_noscreen, monkeypatch):
    # no serial numbers in config is ordered in config order
    minimal_conf_noscreen.screens = [Screen(), Screen()]

    def the_order(self) -> list[Output]:
        return [
            Output(None, None, None, "a", ScreenRect(0, 0, 800, 600)),
            Output(None, None, None, "b", ScreenRect(800, 0, 800, 600)),
        ]

    monkeypatch.setattr(
        f"libqtile.backend.{manager_nospawn.backend.name}.core.Core.get_output_info", the_order
    )
    manager_nospawn.start(minimal_conf_noscreen)
    assert manager_nospawn.c.screen[0].info()["serial"] == "a"
    assert manager_nospawn.c.screen[1].info()["serial"] == "b"


def make_screen(name: str | None = None, serial: str | None = None, text: str = "") -> Screen:
    return Screen(name=name, serial=serial, top=Bar([TextBox(text)], 10))


def test_screen_serial_ordering_one_serial(manager_nospawn, minimal_conf_noscreen, monkeypatch):
    # one serial number is allowed, serial re-use overwrites to avoid confusion
    minimal_conf_noscreen.screens = [Screen(), make_screen(serial="one", text="one")]

    def the_order(self) -> list[Output]:
        return [
            Output(None, None, None, "one", ScreenRect(0, 0, 800, 600)),
            Output(None, None, None, "a", ScreenRect(800, 0, 800, 600)),
        ]

    monkeypatch.setattr(
        f"libqtile.backend.{manager_nospawn.backend.name}.core.Core.get_output_info", the_order
    )
    manager_nospawn.start(minimal_conf_noscreen)
    assert manager_nospawn.c.screen[0].bar["top"].widget["textbox"].get() == "one"
    assert manager_nospawn.c.screen[0].info()["serial"] == "one"
    assert manager_nospawn.c.screen[1].bar["top"].widget["textbox"].get() == "one"
    assert manager_nospawn.c.screen[1].info()["serial"] == "a"


def test_screen_serial_ordering_serials_backwards(
    manager_nospawn, minimal_conf_noscreen, monkeypatch
):
    # when the backend renders serial numbers reverse of config, they should be
    # in config order
    minimal_conf_noscreen.screens = [
        make_screen(serial="one", text="one"),
        make_screen(serial="two", text="two"),
    ]

    def the_order(self) -> list[Output]:
        return [
            Output(None, None, None, "two", ScreenRect(0, 0, 800, 600)),
            Output(None, None, None, "one", ScreenRect(800, 0, 800, 600)),
        ]

    monkeypatch.setattr(
        f"libqtile.backend.{manager_nospawn.backend.name}.core.Core.get_output_info", the_order
    )
    manager_nospawn.start(minimal_conf_noscreen)
    assert manager_nospawn.c.screen[0].info()["serial"] == "two"
    assert manager_nospawn.c.screen[0].bar["top"].widget["textbox"].get() == "two"
    assert manager_nospawn.c.screen[1].info()["serial"] == "one"
    assert manager_nospawn.c.screen[1].bar["top"].widget["textbox"].get() == "one"


def test_screen_serial_ordering_one_name(manager_nospawn, minimal_conf_noscreen, monkeypatch):
    # one output name is allowed, output name re-use overwrites to avoid confusion
    minimal_conf_noscreen.screens = [Screen(), make_screen(name="one", text="one")]

    def the_order(self) -> list[Output]:
        return [
            Output("one", None, None, None, ScreenRect(0, 0, 800, 600)),
            Output("a", None, None, None, ScreenRect(800, 0, 800, 600)),
        ]

    monkeypatch.setattr(
        f"libqtile.backend.{manager_nospawn.backend.name}.core.Core.get_output_info", the_order
    )
    manager_nospawn.start(minimal_conf_noscreen)
    assert manager_nospawn.c.screen[0].bar["top"].widget["textbox"].get() == "one"
    assert manager_nospawn.c.screen[0].info()["name"] == "one"
    assert manager_nospawn.c.screen[1].bar["top"].widget["textbox"].get() == "one"
    assert manager_nospawn.c.screen[1].info()["name"] == "a"


def test_screen_name_ordering_names_backwards(
    manager_nospawn, minimal_conf_noscreen, monkeypatch
):
    # when the backend renders named outputs reverse of config, they should be
    # in config order
    minimal_conf_noscreen.screens = [
        make_screen(name="one", text="one"),
        make_screen(name="two", text="two"),
    ]

    def the_order(self) -> list[Output]:
        return [
            Output("two", None, None, None, ScreenRect(0, 0, 800, 600)),
            Output("one", None, None, None, ScreenRect(800, 0, 800, 600)),
        ]

    monkeypatch.setattr(
        f"libqtile.backend.{manager_nospawn.backend.name}.core.Core.get_output_info", the_order
    )
    manager_nospawn.start(minimal_conf_noscreen)
    assert manager_nospawn.c.screen[0].info()["name"] == "two"
    assert manager_nospawn.c.screen[0].bar["top"].widget["textbox"].get() == "two"
    assert manager_nospawn.c.screen[1].info()["name"] == "one"
    assert manager_nospawn.c.screen[1].bar["top"].widget["textbox"].get() == "one"
