import sys
from importlib import reload
from types import ModuleType

from libqtile.widget import gmail_checker
from test.widgets.conftest import FakeBar


class FakeIMAP(ModuleType):
    class IMAP4_SSL:  # noqa: N801
        def __init__(self, *args, **kwargs):
            pass

        def login(self, username, password):
            self.username = username
            self.password = password

        def status(self, path, *args, **kwargs):
            if not (self.username and self.password):
                return False, None

            return ("OK", [f'("{path}" (MESSAGES 10 UNSEEN 2)'.encode()])


def test_gmail_checker_valid_response(fake_qtile, monkeypatch, fake_window):
    monkeypatch.setitem(sys.modules, "imaplib", FakeIMAP("imaplib"))
    reload(gmail_checker)

    gmc = gmail_checker.GmailChecker(username="qtile", password="test")
    fakebar = FakeBar([gmc], window=fake_window)
    gmc._configure(fake_qtile, fakebar)
    text = gmc.poll()
    assert text == "inbox[10],unseen[2]"


def test_gmail_checker_invalid_response(fake_qtile, monkeypatch, fake_window):
    monkeypatch.setitem(sys.modules, "imaplib", FakeIMAP("imaplib"))
    reload(gmail_checker)

    gmc = gmail_checker.GmailChecker()
    fakebar = FakeBar([gmc], window=fake_window)
    gmc._configure(fake_qtile, fakebar)
    text = gmc.poll()
    assert text == "UNKNOWN ERROR"


# This test is only required because the widget is written
# inefficiently. display_fmt should use keys instead of indices.
def test_gmail_checker_only_unseen(fake_qtile, monkeypatch, fake_window):
    monkeypatch.setitem(sys.modules, "imaplib", FakeIMAP("imaplib"))
    reload(gmail_checker)

    gmc = gmail_checker.GmailChecker(
        display_fmt="unseen[{0}]", status_only_unseen=True, username="qtile", password="test"
    )
    fakebar = FakeBar([gmc], window=fake_window)
    gmc._configure(fake_qtile, fakebar)
    text = gmc.poll()
    assert text == "unseen[2]"
