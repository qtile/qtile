import subprocess
import sys
from pathlib import Path

import pytest

from libqtile import config, confreader, utils
from libqtile.bar import Bar
from libqtile.config import Output, Screen, ScreenRect
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


def test_reload_config_submodules_subprocess(tmp_path):
    """
    Regression test for https://github.com/qtile/qtile/issues/5877

    When qtile is started from a script installed inside the config folder
    (e.g. inside a venv), sys.modules['__main__'].__file__ is inside the
    config directory. _reload_config_submodules must walk imported submodules
    starting from the top-level config module rather than attempting to reload
    __main__ or all files in the directory.
    """
    config_file = tmp_path / "config.py"
    config_file.write_text("import helper\nwmname = f'qtile_{helper.VAL}'\n")

    helper_file = tmp_path / "helper.py"
    helper_file.write_text("VAL = 1\n")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    runner_file = bin_dir / "runner.py"

    runner_file.write_text(f"""
import importlib
import sys
import time
from pathlib import Path
from libqtile import confreader

sys.dont_write_bytecode = True

config_path = Path({repr(str(config_file))})
cfg1 = confreader.Config(config_path)
cfg1.load()
assert cfg1.wmname == "qtile_1", f"Expected qtile_1, got {{cfg1.wmname}}"

time.sleep(0.01)
helper_path = Path({repr(str(helper_file))})
helper_path.write_text("VAL = 2\\n")
importlib.invalidate_caches()

cfg2 = confreader.Config(config_path)
cfg2.load()

assert cfg2.wmname == "qtile_2", f"Expected qtile_2, got {{cfg2.wmname}}"
print("SUCCESS")
""")

    res = subprocess.run(
        [sys.executable, str(runner_file)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0, (
        f"Subprocess failed:\nstdout:\n{res.stdout}\nstderr:\n{res.stderr}"
    )
    assert "SUCCESS" in res.stdout


def test_reload_config_nested_submodules(tmp_path):
    """
    Tests that _reload_config_submodules recursively walks and reloads
    submodule dependencies.
    """
    config_file = tmp_path / "config.py"
    config_file.write_text("from sub1 import get_val\nwmname = f'qtile_{get_val()}'\n")

    sub1_file = tmp_path / "sub1.py"
    sub1_file.write_text("import sub2\ndef get_val():\n    return sub2.VAL\n")

    sub2_file = tmp_path / "sub2.py"
    sub2_file.write_text("VAL = 10\n")

    runner_file = tmp_path / "runner.py"
    runner_file.write_text(f"""
import importlib
import sys
import time
from pathlib import Path
from libqtile import confreader

sys.dont_write_bytecode = True

config_path = Path({repr(str(config_file))})
cfg1 = confreader.Config(config_path)
cfg1.load()
assert cfg1.wmname == "qtile_10"

time.sleep(0.01)
sub2_path = Path({repr(str(sub2_file))})
sub2_path.write_text("VAL = 20\\n")
importlib.invalidate_caches()

cfg2 = confreader.Config(config_path)
cfg2.load()
assert cfg2.wmname == "qtile_20", f"Expected qtile_20, got {{cfg2.wmname}}"
print("SUCCESS")
""")

    res = subprocess.run(
        [sys.executable, str(runner_file)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0, (
        f"Subprocess failed:\nstdout:\n{res.stdout}\nstderr:\n{res.stderr}"
    )
    assert "SUCCESS" in res.stdout


def test_reload_config_submodules_edge_cases(tmp_path):
    """
    Tests edge cases in _reload_config_submodules:
    - Deleted submodule files on disk
    - Non-ModuleType entries in sys.modules
    - Spec-less dynamic modules
    - Objects with throwing attribute access in module namespace
    """
    config_file = tmp_path / "config.py"
    config_file.write_text("import helper\nwmname = f'qtile_{helper.VAL}'\n")

    helper_file = tmp_path / "helper.py"
    helper_file.write_text("VAL = 1\n")

    runner_file = tmp_path / "runner.py"
    runner_file.write_text(f"""
import importlib
import sys
from types import ModuleType
from pathlib import Path
from libqtile import confreader

class ThrowingAttr:
    @property
    def __module__(self):
        raise RuntimeError("Attribute access failed")

sys.dont_write_bytecode = True

config_path = Path({repr(str(config_file))})
cfg1 = confreader.Config(config_path)
cfg1.load()

top_mod = sys.modules["config"]
top_mod.bad_obj = ThrowingAttr()

specless_mod = ModuleType("specless")
specless_mod.__file__ = str(Path({repr(str(tmp_path))}) / "specless.py")
specless_mod.__spec__ = None
(Path({repr(str(tmp_path))}) / "specless.py").write_text("# specless")
top_mod.specless = specless_mod

sys.modules["stub_module"] = None

helper_path = Path({repr(str(helper_file))})
helper_path.unlink()

cfg2 = confreader.Config(config_path)
cfg2._reload_config_submodules(config_path)

sys.modules["config"] = None
cfg2._reload_config_submodules(config_path)

print("SUCCESS")
""")

    res = subprocess.run(
        [sys.executable, str(runner_file)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0, (
        f"Subprocess failed:\nstdout:\n{res.stdout}\nstderr:\n{res.stderr}"
    )
    assert "SUCCESS" in res.stdout


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


def make_screen(text: str = "") -> Screen:
    screen = Screen(top=Bar([TextBox(text)], 10))
    return screen


def test_generate_screens_too_few(manager_nospawn, minimal_conf_noscreen, monkeypatch):
    # generate_screens returns fewer screens than outputs; extra outputs should
    # get default Screen() objects
    def gen_screens(outputs: list[Output]) -> list[Screen]:
        # Only return one screen even though there are two outputs
        return [make_screen(text="first")]

    minimal_conf_noscreen.generate_screens = staticmethod(gen_screens)

    def two_outputs(self) -> list[Output]:
        return [
            Output("DP-1", None, None, "serial_a", ScreenRect(0, 0, 800, 600)),
            Output("DP-2", None, None, "serial_b", ScreenRect(800, 0, 800, 600)),
        ]

    monkeypatch.setattr(
        f"libqtile.backend.{manager_nospawn.backend.name}.core.Core.get_output_info", two_outputs
    )
    manager_nospawn.start(minimal_conf_noscreen)

    # First screen should use the generated screen config
    assert manager_nospawn.c.screen[0].bar["top"].widget["textbox"].get() == "first"
    assert manager_nospawn.c.screen[0].info()["serial"] == "serial_a"

    # Second screen should be a default Screen (auto-created, no custom bar)
    assert manager_nospawn.c.screen[1].info()["serial"] == "serial_b"
    # Verify both screens exist
    assert len(manager_nospawn.c.get_screens()) == 2


def test_generate_screens_too_many(manager_nospawn, minimal_conf_noscreen, monkeypatch):
    # generate_screens returns more screens than outputs; extra screens should
    # be ignored
    def gen_screens(outputs: list[Output]) -> list[Screen]:
        # Return three screens even though there's only one output
        return [
            make_screen(text="first"),
            make_screen(text="second"),
            make_screen(text="third"),
        ]

    minimal_conf_noscreen.generate_screens = staticmethod(gen_screens)

    def one_output(self) -> list[Output]:
        return [
            Output("DP-1", None, None, "serial_a", ScreenRect(0, 0, 800, 600)),
        ]

    monkeypatch.setattr(
        f"libqtile.backend.{manager_nospawn.backend.name}.core.Core.get_output_info", one_output
    )
    manager_nospawn.start(minimal_conf_noscreen)

    # Only one screen should exist (matching the single output)
    assert len(manager_nospawn.c.get_screens()) == 1
    assert manager_nospawn.c.screen[0].bar["top"].widget["textbox"].get() == "first"
    assert manager_nospawn.c.screen[0].info()["serial"] == "serial_a"


def test_generate_screens_serial_matching(manager_nospawn, minimal_conf_noscreen, monkeypatch):
    # generate_screens can inspect output serial numbers and return screens
    # in a specific order based on them
    def gen_screens(outputs: list[Output]) -> list[Screen]:
        screens = []
        for output in outputs:
            if output.serial == "monitor_left":
                screens.append(make_screen(text="left_config"))
            elif output.serial == "monitor_right":
                screens.append(make_screen(text="right_config"))
            else:
                screens.append(Screen())
        return screens

    minimal_conf_noscreen.generate_screens = staticmethod(gen_screens)

    def two_outputs(self) -> list[Output]:
        return [
            Output("DP-1", None, None, "monitor_left", ScreenRect(0, 0, 800, 600)),
            Output("DP-2", None, None, "monitor_right", ScreenRect(800, 0, 800, 600)),
        ]

    monkeypatch.setattr(
        f"libqtile.backend.{manager_nospawn.backend.name}.core.Core.get_output_info", two_outputs
    )
    manager_nospawn.start(minimal_conf_noscreen)

    # Verify screens got the correct config based on their serial number
    assert manager_nospawn.c.screen[0].bar["top"].widget["textbox"].get() == "left_config"
    assert manager_nospawn.c.screen[0].info()["serial"] == "monitor_left"
    assert manager_nospawn.c.screen[1].bar["top"].widget["textbox"].get() == "right_config"
    assert manager_nospawn.c.screen[1].info()["serial"] == "monitor_right"
