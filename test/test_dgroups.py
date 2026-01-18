import time

import pytest

import libqtile
from test.helpers import Retry


class DGroupsConfig(libqtile.confreader.Config):
    auto_fullscreen = True
    groups = [libqtile.config.Group("a"), libqtile.config.Group("b")]
    layouts = [libqtile.layout.MonadTall()]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []


class DGroupsSpawnConfig(DGroupsConfig):
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b", spawn=["xterm"]),
    ]


dgroups_config = pytest.mark.parametrize("manager", [DGroupsConfig], indirect=True)
dgroups_spawn_config = pytest.mark.parametrize("manager", [DGroupsSpawnConfig], indirect=True)


@dgroups_config
def test_dgroup_persist(manager):
    # create dgroup
    gname = "c"
    manager.c.addgroup(gname, persist=True)

    # switch to dgroup
    manager.c.group[gname].toscreen()

    # start window
    one = manager.test_window("test1")

    # close window
    manager.kill_window(one)

    # wait for window to close and group to NOT be destroyed
    time.sleep(2)

    # check if dgroup still exists
    assert len(manager.c.get_groups()) == 3


@dgroups_config
def test_dgroup_nonpersist(manager):
    # create dgroup
    gname = "c"
    manager.c.addgroup(gname)

    # switch to dgroup
    manager.c.group[gname].toscreen()

    # start window
    one = manager.test_window("test1")

    # close window
    manager.kill_window(one)

    # wait for window to close and group to be destroyed
    time.sleep(2)

    # check if dgroup does not exist anymore
    assert len(manager.c.get_groups()) == 2


@dgroups_spawn_config
def test_dgroup_spawn_in_group(manager, backend_name):
    if backend_name == "wayland":
        pytest.skip("TODO: X11 only for now.")

    @Retry(ignore_exceptions=(AssertionError,), tmax=10)
    def wait_for_window():
        assert len(manager.c.windows()) > 0

    wait_for_window()
    assert not manager.c.group["a"].info()["windows"]
    assert manager.c.group["b"].info()["windows"]
