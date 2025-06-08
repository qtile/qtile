# Copyright (c) 2025 e-devnull
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

from libqtile.widget import NetUP
from test.widgets.conftest import FakeBar


def test_host_is_empty():
    netup = NetUP()
    assert netup.poll() == "N/A"


def test_invalid_method():
    netup = NetUP(host="localhost", method="icmp")
    assert netup.poll() == "N/A"


def test_invalid_port():
    netup = NetUP(host="localhost", method="tcp", port="port")
    assert netup.poll() == "N/A"


def test_ping_success(monkeypatch, fake_qtile, fake_window):
    def mock_ping(*args, **kwargs):
        class MockResult:
            def __init__(self, returncode):
                self.returncode = returncode

        return MockResult(returncode=0)

    monkeypatch.setattr("libqtile.widget.netup.run", mock_ping)
    netup = NetUP(host="localhost", method="ping")
    fakebar = FakeBar([netup], window=fake_window)
    netup._configure(fake_qtile, fakebar)

    assert netup.poll() == "NET " + netup.up_string
    assert netup.layout.colour == netup.up_foreground


def test_ping_fail(monkeypatch, fake_qtile, fake_window):
    def mock_ping(*args, **kwargs):
        class MockResult:
            def __init__(self, returncode):
                self.returncode = returncode

        return MockResult(returncode=1)

    monkeypatch.setattr("libqtile.widget.netup.run", mock_ping)
    netup = NetUP(host="localhost", method="ping")
    fakebar = FakeBar([netup], window=fake_window)
    netup._configure(fake_qtile, fakebar)

    assert netup.poll() == "NET " + netup.down_string
    assert netup.layout.colour == netup.down_foreground


def test_tcp_success(monkeypatch, fake_qtile, fake_window):
    def mock_check_tcp(*args, **kwargs):
        return 0

    monkeypatch.setattr(NetUP, "check_tcp", mock_check_tcp)
    netup = NetUP(host="localhost", method="tcp", port=443)
    fakebar = FakeBar([netup], window=fake_window)
    netup._configure(fake_qtile, fakebar)

    assert netup.poll() == "NET " + netup.up_string
    assert netup.layout.colour == netup.up_foreground


def test_tcp_fail(monkeypatch, fake_qtile, fake_window):
    def mock_check_tcp(*args, **kwargs):
        return -1

    monkeypatch.setattr(NetUP, "check_tcp", mock_check_tcp)
    netup = NetUP(host="localhost", method="tcp", port=443)
    fakebar = FakeBar([netup], window=fake_window)
    netup._configure(fake_qtile, fakebar)

    assert netup.poll() == "NET " + netup.down_string
    assert netup.layout.colour == netup.down_foreground
