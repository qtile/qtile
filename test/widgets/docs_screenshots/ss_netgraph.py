import random
import sys
from importlib import reload
from types import ModuleType

import pytest

values = []
for _ in range(100):
    odds = random.randint(0, 10)
    val = 0 if odds < 8 else random.randint(1000, 8000)
    values.append(val)


class MockPsutil(ModuleType):
    up = 0
    down = 0

    @classmethod
    def net_io_counters(cls, pernic=False, _nowrap=True):
        class IOCounters:
            def __init__(self):
                self.bytes_sent = 100
                self.bytes_recv = 1034

        if pernic:
            return {"wlp58s0": IOCounters(), "lo": IOCounters()}
        return IOCounters()


@pytest.fixture
def widget(monkeypatch):
    monkeypatch.setitem(sys.modules, "psutil", MockPsutil("psutil"))
    from libqtile.widget import graph

    reload(graph)
    yield graph.NetGraph


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
def ss_netgraph(screenshot_manager):
    widget = screenshot_manager.c.widget["netgraph"]
    widget.eval(f"self.values={values}")
    widget.eval(f"self.maxvalue={max(values)}")
    widget.eval("self.draw()")
    screenshot_manager.take_screenshot()
