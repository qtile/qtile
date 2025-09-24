import pytest

import libqtile.bar
import libqtile.config
import libqtile.layout
from libqtile.confreader import Config
from libqtile.extension.window_list import WindowList
from libqtile.lazy import lazy


@pytest.fixture
def extension_manager(monkeypatch, manager_nospawn):
    extension = WindowList()

    # We want the value returned immediately
    def fake_popen(cmd, *args, **kwargs):
        class PopenObj:
            def communicate(self, value_in, *args):
                return [value_in, None]

        return PopenObj()

    monkeypatch.setattr("libqtile.extension.base.Popen", fake_popen)

    class ManagerConfig(Config):
        groups = [
            libqtile.config.Group("a"),
            libqtile.config.Group("b"),
        ]
        layouts = [libqtile.layout.max.Max()]
        keys = [
            libqtile.config.Key(["control"], "k", lazy.run_extension(extension)),
        ]
        screens = [
            libqtile.config.Screen(
                bottom=libqtile.bar.Bar([], 20),
            )
        ]

    manager_nospawn.start(ManagerConfig)

    yield manager_nospawn


def test_window_list(extension_manager):
    """Test WindowList extension switches group."""

    # Launch a window and verify it's on the current group
    extension_manager.test_window("one")
    assert len(extension_manager.c.group.info()["windows"]) == 1

    # Switch group and verify no windows in group
    extension_manager.c.group["b"].toscreen()
    assert len(extension_manager.c.group.info()["windows"]) == 0

    # Toggle extension (which is patched to return immediately)
    # Check that window is visible on original group
    extension_manager.c.simulate_keypress(["control"], "k")
    assert len(extension_manager.c.group.info()["windows"]) == 1
    assert extension_manager.c.group.info()["label"] == "a"
