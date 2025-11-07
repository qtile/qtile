import builtins

import pytest

IW_OUTPUT = """
Connected to a0:40:a0:80:fe:0e (on wlan0)
	SSID: QtileNet
	freq: 5765.0
	RX: 16284577 bytes (19232 packets)
	TX: 3135164 bytes (8380 packets)
	signal: -60 dBm
	rx bitrate: 526.6 MBit/s VHT-MCS 6 80MHz VHT-NSS 2
	tx bitrate: 325.0 MBit/s VHT-MCS 7 80MHz short GI VHT-NSS 1
	bss flags: short-slot-time
	dtim period: 2
	beacon int: 101
""".strip()

IW_OUTPUT_NO_CONN = "command failed: No such device (-19)"

IP_ADDRESS = "192.1.1.62"


def mock_open(output):
    class MockOpen:
        def __init__(self, *args):
            self.output = output

        def __enter__(self):
            return self

        def __exit__(*exc):
            return None

        def read(self):
            return self.output

    return MockOpen


def mock_subprocess_run_get_ip(*args, **kwargs):
    class IP:
        @property
        def stdout(self):
            return f"wlan        UP             {IP_ADDRESS}/24 fe80::f9c:223f:324a:30dc/64"

    return IP()


@pytest.fixture
def patched_wlaniw(monkeypatch):
    from libqtile.widget import wlaniw

    monkeypatch.setattr(wlaniw.subprocess, "run", mock_subprocess_run_get_ip)
    yield wlaniw


def test_wifi(patched_wlaniw):
    widget = patched_wlaniw.WlanIw()
    out = widget.parse(IW_OUTPUT)
    assert out == f"QtileNet {-60 + 110}/70"

    widget = patched_wlaniw.WlanIw(format="{essid} {percent:2.0%}")
    out = widget.parse(IW_OUTPUT)
    assert out == "QtileNet 71%"

    widget = patched_wlaniw.WlanIw(format="{ipaddr}")
    out = widget.parse(IW_OUTPUT)
    assert out == IP_ADDRESS


def test_wifi_no_connection(patched_wlaniw):
    widget = patched_wlaniw.WlanIw()
    out = widget.parse(IW_OUTPUT_NO_CONN)
    assert out == "Disconnected"


@pytest.mark.parametrize(
    "kwargs,state,expected",
    [
        ({"use_ethernet": True}, "up", "eth"),
        ({"use_ethernet": True}, "down", "Disconnected"),
        ({"use_ethernet": True, "ethernet_message_format": "Wired"}, "up", "Wired"),
    ],
)
def test_ethernet(patched_wlaniw, kwargs, state, expected, monkeypatch):
    monkeypatch.setattr(builtins, "open", mock_open(state))
    widget = patched_wlaniw.WlanIw(**kwargs)
    assert widget.parse("") == expected
