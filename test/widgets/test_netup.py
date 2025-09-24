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
