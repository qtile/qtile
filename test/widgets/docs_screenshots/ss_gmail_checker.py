import sys
from importlib import reload

import pytest

from libqtile.widget import gmail_checker
from test.widgets.test_gmail_checker import FakeIMAP


@pytest.fixture
def widget(monkeypatch):
    monkeypatch.setitem(sys.modules, "imaplib", FakeIMAP("imaplib"))
    reload(gmail_checker)
    yield gmail_checker.GmailChecker


@pytest.mark.parametrize(
    "screenshot_manager",
    [
        {"username": "qtile", "password": "qtile"},
        {
            "username": "qtile",
            "password": "qtile",
            "display_fmt": "unseen[{0}]",
            "status_only_unseen": True,
        },
    ],
    indirect=True,
)
def ss_gmail_checker(screenshot_manager):
    screenshot_manager.take_screenshot()


# # This test is only required because the widget is written
# # inefficiently. display_fmt should use keys instead of indices.
# def test_gmail_checker_only_unseen(fake_qtile, monkeypatch, fake_window):
#     monkeypatch.setitem(sys.modules, "imaplib", FakeIMAP("imaplib"))
#     reload(gmail_checker)

#     gmc = gmail_checker.GmailChecker(
#         display_fmt="unseen[{0}]",
#         status_only_unseen=True,
#         username="qtile",
#         password="test"
#     )
#     fakebar = FakeBar([gmc], window=fake_window)
#     gmc._configure(fake_qtile, fakebar)
#     text = gmc.poll()
#     assert text == "unseen[2]"
