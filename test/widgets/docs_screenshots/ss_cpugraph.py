import random
import sys
from importlib import reload
from types import ModuleType

import pytest

values = []
val = 25.0
for _ in range(100):
    adjust = random.uniform(-2.0, 2.0)
    val += adjust
    values.append(val)


class MockPsutil(ModuleType):
    @classmethod
    def cpu_times(cls):
        class CPU:
            user = 0.5
            nice = 0.5
            system = 0.5
            idle = 0.5

        return CPU()


@pytest.fixture
def widget(monkeypatch):
    monkeypatch.setitem(sys.modules, "psutil", MockPsutil("psutil"))
    from libqtile.widget import graph

    reload(graph)
    yield graph.CPUGraph


@pytest.mark.parametrize(
    "screenshot_manager",
    [
        {},
        {"type": "box"},
        {"type": "line"},
        {"type": "line", "line_width": 1},
        {"start_pos": "top"},
    ],
    indirect=True,
)
def ss_cpugraph(screenshot_manager):
    widget = screenshot_manager.c.widget["cpugraph"]
    widget.eval(f"self.values={values}")
    widget.eval("self.draw()")
    screenshot_manager.take_screenshot()
