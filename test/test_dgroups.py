# Copyright (c) 2024 Thomas Krug
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

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
def test_dgroup_spawn_in_group(manager):
    @Retry(ignore_exceptions=(AssertionError,))
    def wait_for_window():
        assert len(manager.c.windows()) > 0

    wait_for_window()
    assert not manager.c.group["a"].info()["windows"]
    assert manager.c.group["b"].info()["windows"]
