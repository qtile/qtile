import sys
from importlib import reload

import pytest

from test.widgets.test_imapwidget import FakeIMAP, FakeKeyring


@pytest.fixture
def widget(monkeypatch):
    monkeypatch.delitem(sys.modules, "imaplib", raising=False)
    monkeypatch.delitem(sys.modules, "keyring", raising=False)
    monkeypatch.setitem(sys.modules, "imaplib", FakeIMAP("imaplib"))
    monkeypatch.setitem(sys.modules, "keyring", FakeKeyring("keyring"))
    from libqtile.widget import imapwidget

    reload(imapwidget)
    yield imapwidget.ImapWidget


@pytest.mark.parametrize("screenshot_manager", [{"user": "qtile"}], indirect=True)
def ss_imapwidget(screenshot_manager):
    screenshot_manager.take_screenshot()
