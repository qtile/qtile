import pytest

from test.conftest import BareConfig
from test.test_manager import ManagerConfig

bare_config = pytest.mark.parametrize("manager", [BareConfig], indirect=True)


@bare_config
def test_info(manager):
    """
    Checks each backend Window implementation provides the required information.
    """
    manager.test_window("one")
    manager.c.sync()
    info = manager.c.window.info()
    assert info["name"] == "one"
    assert info["group"] == "a"
    assert info["wm_class"][0] == "TestWindow"
    assert "x" in info
    assert "y" in info
    assert "width" in info
    assert "height" in info
    assert "id" in info


@bare_config
def test_margin(manager):
    manager.test_window("one")

    # No margin
    manager.c.window.place(10, 20, 50, 60, 0, "000000")
    assert manager.c.window.info()["x"] == 10
    assert manager.c.window.info()["y"] == 20
    assert manager.c.window.info()["width"] == 50
    assert manager.c.window.info()["height"] == 60

    # Margin as int
    manager.c.window.place(10, 20, 50, 60, 0, "000000", margin=8)
    assert manager.c.window.info()["x"] == 18
    assert manager.c.window.info()["y"] == 28
    assert manager.c.window.info()["width"] == 34
    assert manager.c.window.info()["height"] == 44

    # Margin as list
    manager.c.window.place(10, 20, 50, 60, 0, "000000", margin=[2, 4, 8, 10])
    assert manager.c.window.info()["x"] == 20
    assert manager.c.window.info()["y"] == 22
    assert manager.c.window.info()["width"] == 36
    assert manager.c.window.info()["height"] == 50


@bare_config
def test_no_size_hint(manager):
    manager.test_window("one")
    manager.c.window.enable_floating()
    assert manager.c.window.info()["width"] == 100
    assert manager.c.window.info()["height"] == 100

    manager.c.window.set_size_floating(50, 50)
    assert manager.c.window.info()["width"] == 50
    assert manager.c.window.info()["height"] == 50

    manager.c.window.set_size_floating(200, 200)
    assert manager.c.window.info()["width"] == 200
    assert manager.c.window.info()["height"] == 200


class BringFrontClickConfig(ManagerConfig):
    bring_front_click = True


class BringFrontClickFloatingOnlyConfig(ManagerConfig):
    bring_front_click = "floating_only"


@pytest.fixture
def bring_front_click(request):
    return request.param


@pytest.mark.parametrize(
    "manager, bring_front_click",
    [
        (ManagerConfig, False),
        (BringFrontClickConfig, True),
        (BringFrontClickFloatingOnlyConfig, "floating_only"),
    ],
    indirect=True,
)
def test_bring_front_click(manager, bring_front_click):
    manager.c.group.setlayout("tile")
    # this is a tiled window.
    manager.test_window("one")

    manager.test_window("two")
    manager.c.window.set_position_floating(50, 50)
    manager.c.window.set_size_floating(50, 50)

    manager.test_window("three")
    manager.c.window.set_position_floating(150, 50)
    manager.c.window.set_size_floating(50, 50)

    wids = [x["id"] for x in manager.c.windows()]
    names = [x["name"] for x in manager.c.windows()]

    assert names == ["one", "two", "three"]
    wins = manager.backend.get_all_windows()
    assert wins.index(wids[0]) < wins.index(wids[1]) < wins.index(wids[2])

    # Click on window two
    manager.backend.fake_click(55, 55)
    assert manager.c.window.info()["name"] == "two"
    wins = manager.backend.get_all_windows()
    if bring_front_click:
        assert wins.index(wids[0]) < wins.index(wids[2]) < wins.index(wids[1])
    else:
        assert wins.index(wids[0]) < wins.index(wids[1]) < wins.index(wids[2])

    # Click on window one
    manager.backend.fake_click(10, 10)
    assert manager.c.window.info()["name"] == "one"
    wins = manager.backend.get_all_windows()
    if bring_front_click == "floating_only":
        assert wins.index(wids[0]) < wins.index(wids[2]) < wins.index(wids[1])
    elif bring_front_click:
        assert wins.index(wids[2]) < wins.index(wids[1]) < wins.index(wids[0])
    else:
        assert wins.index(wids[0]) < wins.index(wids[1]) < wins.index(wids[2])
