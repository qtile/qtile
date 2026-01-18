import pytest

from libqtile.widget import idlerpg
from test.widgets.test_idlerpg import online_response


@pytest.fixture
def widget(monkeypatch):
    def no_op(*args, **kwargs):
        return ""

    idler = idlerpg.IdleRPG
    idler.RESPONSE = online_response
    yield idler


@pytest.mark.parametrize(
    "screenshot_manager",
    [{"url": "http://idlerpg.qtile.org?player=elParaguayo"}],
    indirect=True,
)
def ss_idlerpg(screenshot_manager):
    screenshot_manager.c.widget["idlerpg"].eval("self.update(self.parse(self.RESPONSE))")
    screenshot_manager.take_screenshot()
