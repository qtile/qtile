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
