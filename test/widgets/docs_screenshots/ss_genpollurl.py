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
import pytest

import libqtile.widget
from test.widgets.test_generic_poll_text import MockRequest, Mockurlopen


@pytest.fixture
def widget(monkeypatch):
    MockRequest.return_value = b"Text from URL"
    monkeypatch.setattr("libqtile.widget.generic_poll_text.Request", MockRequest)
    monkeypatch.setattr("libqtile.widget.generic_poll_text.urlopen", Mockurlopen)
    yield libqtile.widget.GenPollUrl


@pytest.mark.parametrize(
    "screenshot_manager",
    [{}, {"url": "http://test.qtile.org", "json": False, "parse": lambda x: x}],
    indirect=True,
)
def ss_genpollurl(screenshot_manager):
    screenshot_manager.take_screenshot()
