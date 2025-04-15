# Copyright (c) 2021 elParaguayo
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Widget specific tests

import sys
from importlib import reload
from types import ModuleType

import pytest

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

            return ("OK", [f'"{path}" (UNSEEN 2)'.encode()])

        def logout(self):
            pass


class FakeKeyring(ModuleType):
    valid = True

    def get_password(self, _app, user):
        if self.valid:
            return "password"
        return None


@pytest.fixture()
def patched_imap(monkeypatch):
    monkeypatch.delitem(sys.modules, "imaplib", raising=False)
    monkeypatch.delitem(sys.modules, "keyring", raising=False)
    monkeypatch.setitem(sys.modules, "imaplib", FakeIMAP("imaplib"))
    monkeypatch.setitem(sys.modules, "keyring", FakeKeyring("keyring"))
    from libqtile.widget import imapwidget

    reload(imapwidget)
    yield imapwidget


def test_imapwidget(fake_qtile, monkeypatch, fake_window, patched_imap):
    imap = patched_imap.ImapWidget(user="qtile")
    fakebar = FakeBar([imap], window=fake_window)
    imap._configure(fake_qtile, fakebar)
    text = imap.poll()
    assert text == "INBOX: 2"


def test_imapwidget_with_password(fake_qtile, monkeypatch, fake_window, patched_imap):
    # keyring should not be called
    patched_imap.keyring.valid = False
    imap = patched_imap.ImapWidget(user="qtile", password="password")
    fakebar = FakeBar([imap], window=fake_window)
    imap._configure(fake_qtile, fakebar)
    text = imap.poll()
    assert text == "INBOX: 2"


def test_imapwidget_password_none(fake_qtile, monkeypatch, fake_window, patched_imap):
    patched_imap.keyring.valid = False

    imap = patched_imap.ImapWidget(user="qtile")
    fakebar = FakeBar([imap], window=fake_window)
    imap._configure(fake_qtile, fakebar)
    text = imap.poll()
    assert text == "No password error"
