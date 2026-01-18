import sys
from importlib import reload
from types import ModuleType

import pytest

values = [100] * 100


class MockPsutil(ModuleType):
    pass


@pytest.fixture
def widget(monkeypatch):
    monkeypatch.setitem(sys.modules, "psutil", MockPsutil("psutil"))
    from libqtile.widget import graph

    reload(graph)
    yield graph.HDDGraph


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
def ss_hddgraph(screenshot_manager):
    widget = screenshot_manager.c.widget["hddgraph"]
    widget.eval(f"self.values={values}")
    widget.eval("self.maxvalue=400")
    widget.eval("self.draw()")
    screenshot_manager.take_screenshot()
