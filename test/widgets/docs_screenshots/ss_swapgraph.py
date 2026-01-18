import random
import sys
from importlib import reload
from types import ModuleType

import pytest

values = []
val = 1500
for _ in range(100):
    adjust = random.uniform(-2.0, 2.0) * 100
    val += adjust
    values.append(val)


class MockPsutil(ModuleType):
    @classmethod
    def swap_memory(cls):
        class Swap:
            total = 8175788032
            free = 2055852032

        return Swap()


@pytest.fixture
def widget(monkeypatch):
    monkeypatch.setitem(sys.modules, "psutil", MockPsutil("psutil"))
    from libqtile.widget import graph

    reload(graph)
    yield graph.SwapGraph


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
def ss_swapgraph(screenshot_manager):
    widget = screenshot_manager.c.widget["swapgraph"]
    widget.eval(f"self.values={values}")
    widget.eval("self.draw()")
    screenshot_manager.take_screenshot()
