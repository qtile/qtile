import sys
from importlib import reload
from types import ModuleType

import pytest

import libqtile.config
import libqtile.widget
from libqtile.bar import Bar


class MockPsutil(ModuleType):
    __version__ = "5.8.0"

    @classmethod
    def cpu_percent(cls):
        return 2.6

    @classmethod
    def cpu_freq(cls):
        class Freq:
            def __init__(self):
                self.current = 500.067
                self.min = 400.0
                self.max = 2800.0

        return Freq()


@pytest.fixture
def cpu_manager(monkeypatch, manager_nospawn, minimal_conf_noscreen):
    monkeypatch.setitem(sys.modules, "psutil", MockPsutil("psutil"))
    from libqtile.widget import cpu

    reload(cpu)

    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=Bar([cpu.CPU()], 10))]

    manager_nospawn.start(config)
    yield manager_nospawn


def test_cpu(cpu_manager):
    assert cpu_manager.c.widget["cpu"].info()["text"] == "CPU 0.5GHz 2.6%"
