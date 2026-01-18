import sys
from importlib import reload

import pytest

from test.widgets.test_net import MockPsutil


@pytest.fixture
def widget(monkeypatch):
    monkeypatch.setitem(sys.modules, "psutil", MockPsutil("psutil"))
    from libqtile.widget import net

    reload(net)
    yield net.Net


@pytest.mark.parametrize(
    "screenshot_manager",
    [
        {},
        {"format": "{interface}: U {up} D {down} T {total}"},
        {
            "format": "{interface}: U {up}{up_suffix} D {down}{down_suffix} T {total}{total_suffix}"
        },
        {"format": "{down:.0f}{down_suffix} \u2193\u2191 {up:.0f}{up_suffix}"},
        {"interface": "wlp58s0"},
        {"prefix": "M"},
    ],
    indirect=True,
)
def ss_net(screenshot_manager):
    screenshot_manager.take_screenshot()
