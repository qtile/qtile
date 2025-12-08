import sys
from types import ModuleType

import pytest

from libqtile.bar import Bar
from libqtile.config import Screen
from libqtile.widget.launchbar import LaunchBar
from test.helpers import BareConfig


class LaunchBarTestWidget(LaunchBar):
    def get_icon_in_position(self, x, y):
        index = LaunchBar.get_icon_in_position(self, x, y)
        if index is not None:
            self.clicked_icon = self.progs[index]["name"]
        else:
            self.clicked_icon = "ERROR"
        return index


class MockXDG(ModuleType):
    def getIconPath(*args, **kwargs):  # noqa: N802
        pass


@pytest.fixture
def position(request):
    return getattr(request, "param", "top")


@pytest.fixture
def progs(request):
    print(getattr(request, "param", ""))
    return getattr(request, "param", [("test", "test", "")])


def set_progs(progs):
    return pytest.mark.parametrize("progs", progs, indirect=True)


horizontal_and_vertical = pytest.mark.parametrize("position", ["top", "left"], indirect=True)


@pytest.fixture
def launchbar_manager(request, manager_nospawn, position, progs):
    config = getattr(request, "param", dict())

    class LaunchBarConfig(BareConfig):
        screens = [
            Screen(
                **{
                    position: Bar(
                        [LaunchBarTestWidget(progs=progs, name="launchbar", padding=0, **config)],
                        28,
                    )
                }
            )
        ]

    manager_nospawn.start(LaunchBarConfig)
    yield manager_nospawn


def test_deprecated_configuration(caplog, monkeypatch):
    monkeypatch.setitem(sys.modules, "xdg.IconTheme", MockXDG("xdg.IconTheme"))
    _ = LaunchBar([("thunderbird", "thunderbird -safe-mode", "launch thunderbird in safe mode")])
    records = [r for r in caplog.records if r.msg.startswith("The use of")]
    assert records
    assert "The use of a positional argument in LaunchBar is deprecated." in records[0].msg


@horizontal_and_vertical
def test_tasklist_defaults(launchbar_manager):
    widget = launchbar_manager.c.widget["launchbar"]
    assert widget.info()["length"] > 0


@pytest.mark.parametrize(
    "position,coords,clicked",
    [
        ("top", (10, 0, 1), "one"),
        ("top", (30, 0, 1), "two"),
        ("left", (0, 30, 1), "one"),
        ("left", (0, 10, 1), "two"),
        ("right", (0, 10, 1), "one"),
        ("right", (0, 30, 1), "two"),
    ],
    indirect=["position"],
)
@set_progs([[("one", "qshell:None", ""), ("two", "qshell:None", "")]])
def test_launchbar_click(launchbar_manager, position, coords, clicked):
    launchbar_manager.c.bar[position].fake_button_press(*coords)
    assert launchbar_manager.c.widget["launchbar"].eval("self.clicked_icon") == clicked
