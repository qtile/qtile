import sys
import tempfile
from importlib import reload
from types import ModuleType

import pytest

import libqtile.config
import libqtile.widget
from libqtile.bar import Bar


class MockPsutil(ModuleType):
    pass


# Set ticks of fake stat file
def set_io_ticks(temp_file, io_ticks):
    temp_file.truncate(0)
    temp_file.write(
        f"13850 7547 1201386 14536 12612 60213 1838656 73847 0 {io_ticks} 112672 0 0 0 0 2116 24287"
    )
    temp_file.flush()


@pytest.fixture
def hdd_manager(monkeypatch, manager_nospawn, minimal_conf_noscreen):
    monkeypatch.setitem(sys.modules, "psutil", MockPsutil("psutil"))
    from libqtile.widget import hdd

    reload(hdd)

    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=Bar([hdd.HDD()], 10))]

    manager_nospawn.start(config)
    yield manager_nospawn


def test_hdd(hdd_manager):
    # Create a fake stat file
    fake_stat_file = tempfile.NamedTemporaryFile(mode="w+", delete=False)

    widget = hdd_manager.c.widget["hdd"]
    widget.eval(f"self.path = '{fake_stat_file.name}'")

    set_io_ticks(fake_stat_file, 0)
    widget.eval("self.update(self.poll())")
    assert widget.info()["text"] == "HDD 0.0%"

    set_io_ticks(fake_stat_file, 300000)
    widget.eval("self.update(self.poll())")
    assert widget.info()["text"] == "HDD 50.0%"

    set_io_ticks(fake_stat_file, 900000)
    widget.eval("self.update(self.poll())")
    assert widget.info()["text"] == "HDD 100.0%"

    set_io_ticks(fake_stat_file, 2000000)
    widget.eval("self.update(self.poll())")
    assert widget.info()["text"] == "HDD 100.0%"

    set_io_ticks(fake_stat_file, 0)
    widget.eval("self.update(self.poll())")
    assert widget.info()["text"] == "HDD 0.0%"
