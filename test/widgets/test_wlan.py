import builtins
import sys
import textwrap
from importlib import reload
from types import ModuleType

import pytest

import libqtile.config
from libqtile.bar import Bar


def no_op(*args, **kwargs):
    pass


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


# see for quality: https://superuser.com/questions/866005/wireless-connection-link-quality-what-does-31-70-indicate
# below are the calculations to relate signal from iw and level from iwlib as
# well as quality from iwlib and signal from iw.
# level = signal + 256
# quality = signal + 110
class MockIwlib(ModuleType):
    DATA = {
        "wlan0": {
            "NWID": b"Auto",
            "Frequency": b"5.18 GHz",
            "Access Point": b"12:34:56:78:90:AB",
            "BitRate": b"650 Mb/s",
            "ESSID": b"QtileNet",
            "Mode": b"Managed",
            "stats": {"quality": 49, "level": 195, "noise": 0, "updated": 75},
        },
        "wlan1": {
            "ESSID": None,
        },
    }

    @classmethod
    def get_iwconfig(cls, interface):
        return cls.DATA.get(interface, dict())


class MockIWSubprocessRun:
    def __call__(self, *args, **kwargs):
        assert len(args) == 1
        cmd = args[0]
        if "wlan0" in cmd:
            _stdout = textwrap.dedent("""
            Connected to 12:34:56:78:90:AB (on wlan0)
                SSID: QtileNet
                freq: 5180.0
                RX: 100109613 bytes (77173 packets)
                TX: 3595242 bytes (19864 packets)
                signal: -61 dBm
                rx bitrate: 780.0 MBit/s VHT-MCS 8 80MHz short GI VHT-NSS 2
                tx bitrate: 650.0 MBit/s VHT-MCS 7 80MHz short GI VHT-NSS 2
                bss flags: short-slot-time
                dtim period: 1
                beacon int: 100""")

        elif "wlan1" in cmd:
            _stdout = "command failed: No such device (-19)"

        else:
            print("--------------------------------------------------")
            print(args)
            print("--------------------------------------------------")
            raise Exception("MockIWSubprocessRun is busted.")

        class MockIwResult:
            @property
            def stdout(self):
                return _stdout

        return MockIwResult()


# Patch the widget with our mock iwlib module.
@pytest.fixture
def patched_wlan(monkeypatch):
    monkeypatch.setitem(sys.modules, "iwlib", MockIwlib("iwlib"))
    from libqtile.widget import wlan

    # Reload fixes cases where psutil may have been imported previously
    reload(wlan)

    yield wlan


@pytest.mark.parametrize(
    "kwargs,expected",
    [
        ({}, "QtileNet 49/70"),
        ({"format": "{essid} {percent:2.0%}"}, "QtileNet 70%"),
        ({"interface": "wlan1"}, "Disconnected"),
    ],
)
def test_wlan_display(minimal_conf_noscreen, manager_nospawn, patched_wlan, kwargs, expected):
    widget = patched_wlan.Wlan(**kwargs)
    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=Bar([widget], 10))]
    manager_nospawn.start(config)

    text = manager_nospawn.c.bar["top"].info()["widgets"][0]["text"]
    assert text == expected


# Patch the widget with our mock iw subprocess call.
@pytest.fixture
def patched_wlan_iw(monkeypatch):
    _ = sys.modules.pop("iwlib", None)
    import importlib

    from libqtile.widget import wlan

    importlib.reload(wlan)
    monkeypatch.setattr(wlan, "_IW_BACKEND", "iw")
    monkeypatch.setattr(wlan.subprocess, "run", MockIWSubprocessRun())
    yield wlan


@pytest.mark.parametrize(
    "kwargs,expected",
    [
        ({}, "QtileNet 49/70"),
        ({"format": "{essid} {percent:2.0%}"}, "QtileNet 70%"),
        ({"interface": "wlan1"}, "Disconnected"),
    ],
)
def test_wlan_display_iw(
    minimal_conf_noscreen, manager_nospawn, patched_wlan_iw, monkeypatch, kwargs, expected
):
    widget = patched_wlan_iw.Wlan(**kwargs)
    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=Bar([widget], 10))]
    manager_nospawn.start(config)
    text = manager_nospawn.c.bar["top"].info()["widgets"][0]["text"]
    assert text == expected


def test_wlan_display_escape_essid(
    minimal_conf_noscreen, manager_nospawn, patched_wlan, monkeypatch
):
    """Test escaping of pango markup in ESSID"""
    monkeypatch.setitem(MockIwlib.DATA["wlan0"], "ESSID", b"A&B")
    widget = patched_wlan.Wlan(format="{essid}")
    assert widget.poll() == "A&amp;B"


@pytest.mark.parametrize(
    "kwargs,state,expected",
    [
        ({"interface": "wlan1", "use_ethernet": True}, "up", "eth"),
        ({"interface": "wlan1", "use_ethernet": True}, "down", "Disconnected"),
        (
            {"interface": "wlan1", "use_ethernet": True, "ethernet_message_format": "Wired"},
            "up",
            "Wired",
        ),
    ],
)
def test_ethernet(
    minimal_conf_noscreen, manager_nospawn, patched_wlan, kwargs, state, expected, monkeypatch
):
    monkeypatch.setattr(builtins, "open", mock_open(state))
    widget = patched_wlan.Wlan(**kwargs)
    assert widget.poll() == expected
