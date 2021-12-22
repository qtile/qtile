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


# Net widget only needs bytes_recv/sent attributes
# Widget displays increase since last poll therefore
# we need to increment value each time this is called.
class MockPsutil(ModuleType):
    up = 0
    down = 0

    @classmethod
    def net_io_counters(cls, pernic=False, _nowrap=True):
        class IOCounters:
            def __init__(self, up, down):
                self.bytes_sent = up
                self.bytes_recv = down

        cls.up += 40000
        cls.down += 1200000

        if pernic:
            return {"wlp58s0": IOCounters(cls.up, cls.down), "lo": IOCounters(cls.up, cls.down)}
        return IOCounters(cls.up, cls.down)


# Patch the widget with our mock psutil module.
# Wrap widget so tests can pass keyword arguments.
@pytest.fixture
def patch_net(fake_qtile, monkeypatch, fake_window):
    def build_widget(**kwargs):
        monkeypatch.setitem(sys.modules, "psutil", MockPsutil("psutil"))
        from libqtile.widget import net

        # Reload fixes cases where psutil may have been imported previously
        reload(net)
        widget = net.Net(format="{interface}: U {up} D {down} T {total}", **kwargs)
        fakebar = FakeBar([widget], window=fake_window)
        widget._configure(fake_qtile, fakebar)

        return widget

    return build_widget


def test_net_defaults(patch_net):
    """Default: widget shows `all` interfaces"""
    net1 = patch_net()
    assert net1.poll() == "all: U 40.00kB D  1.20MB T  1.24MB"


def test_net_single_interface(patch_net):
    """Display single named interface"""
    net2 = patch_net(interface="wlp58s0")
    assert net2.poll() == "wlp58s0: U 40.00kB D  1.20MB T  1.24MB"


def test_net_list_interface(patch_net):
    """Display multiple named interfaces"""
    net2 = patch_net(interface=["wlp58s0", "lo"])
    assert (
        net2.poll() == "wlp58s0: U 40.00kB D  1.20MB T  1.24MB lo: U 40.00kB D  1.20MB T  1.24MB"
    )


def test_net_invalid_interface(patch_net):
    """Pass an invalid interface value"""
    with pytest.raises(AttributeError):
        _ = patch_net(interface=12)


def test_net_use_bits(patch_net):
    """Display all interfaces in bits rather than bytes"""
    net4 = patch_net(use_bits=True)
    assert net4.poll() == "all: U 320.0kb D  9.60Mb T  9.92Mb"


def test_net_convert_zero_b(patch_net):
    """Zero bytes is a special case in `convert_b`"""
    net5 = patch_net()
    assert net5.convert_b(0.0) == (0.0, "B")


def test_net_use_prefix(patch_net):
    """Tests `prefix` configurable option"""
    net6 = patch_net(prefix="M")
    assert net6.poll() == "all: U  0.04MB D  1.20MB T  1.24MB"


# Untested: 128-129 - generic exception catching
