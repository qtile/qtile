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

from libqtile.bar import Bar


def no_op(*args, **kwargs):
    pass


# Net widget only needs bytes_recv/sent attributes
# Widget displays increase since last poll therefore
# we need to increment value each time this is called.
class MockPsutil(ModuleType):
    up = 0
    down = 0

    @classmethod
    def net_io_counters(cls, pernic=False, nowrap=True):

        class IOCounters:
            def __init__(self, up, down):
                self.bytes_sent = up
                self.bytes_recv = down

        cls.up += 40000
        cls.down += 1200000

        if pernic:
            return {
                "wlp58s0": IOCounters(cls.up, cls.down),
                "lo": IOCounters(cls.up, cls.down)
            }
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
        widget = net.Net(
                format='{interface}: U {up} D {down} T {total} DS {size_down} US {size_up}',
                **kwargs
            )
        fakebar = Bar([widget], 24)
        fakebar.window = fake_window
        fakebar.width = 10
        fakebar.height = 10
        fakebar.draw = no_op
        widget._configure(fake_qtile, fakebar)

        return widget
    return build_widget


def test_net_defaults_si_prefix(patch_net):
    '''Default: widget shows `all` interfaces'''
    net1 = patch_net()
    assert net1.poll() == "all: U 40.00kB D  1.20MB T  1.24MB DS  2.40MB US 80.00kB"

def test_net_defaults_binnary_prefix(patch_net):
    '''Default: widget shows `all` interfaces'''
    net1 = patch_net(factor=1024)
    assert net1.poll() == "all: U 39.06kiB D  1.14MiB T  1.18MiB DS  4.58MiB US 156.2kiB"

def test_net_single_interface_si_prefix(patch_net):
    '''Display single named interface'''
    net2 = patch_net(interface="wlp58s0")
    assert net2.poll() == "wlp58s0: U 40.00kB D  1.20MB T  1.24MB DS  7.20MB US 240.0kB"

def test_net_single_interface_binnary_prefix(patch_net):
    '''Display single named interface'''
    net2 = patch_net(interface="wlp58s0", factor=1024)
    assert net2.poll() == "wlp58s0: U 39.06kiB D  1.14MiB T  1.18MiB DS  9.16MiB US 312.5kiB"


def test_net_list_interface_si_prefix(patch_net):
    '''Display multiple named interfaces'''
    net3 = patch_net(interface=["wlp58s0", "lo"])
    assert net3.poll() == "wlp58s0: U 40.00kB D  1.20MB T  1.24MB DS 12.00MB US 400.0kB lo: U 40.00kB D  1.20MB T  1.24MB DS 12.00MB US 400.0kB"

def test_net_list_interface_binnary_prefix(patch_net):
    '''Display multiple named interfaces'''
    net3 = patch_net(interface=["wlp58s0", "lo"], factor=1024)
    assert net3.poll() == "wlp58s0: U 39.06kiB D  1.14MiB T  1.18MiB DS 13.73MiB US 468.7kiB lo: U 39.06kiB D  1.14MiB T  1.18MiB DS 13.73MiB US 468.7kiB"

def test_net_invalid_interface(patch_net):
    '''Pass an invalid interface value'''
    with pytest.raises(AttributeError):
        _ = patch_net(interface=12)

def test_net_use_bits_si_prefix(patch_net):
    '''Display all interfaces in bits rather than bytes'''
    net4 = patch_net(use_bits=True)
    assert net4.poll() == "all: U 320.0kb D  9.60Mb T  9.92Mb DS 134.4Mb US  4.48Mb"

def test_net_use_bits_binnary_prefix(patch_net):
    '''Display all interfaces in bits rather than bytes'''
    net4 = patch_net(use_bits=True, factor=1024)
    assert net4.poll() == "all: U 312.5kib D  9.16Mib T  9.46Mib DS 146.4Mib US  4.88Mib"

def test_net_convert_zero_b(patch_net):
    '''Zero bytes is a special case in `convert_b`'''
    net5 = patch_net()
    assert net5.convert_b(0.0) == (0.0, "B")


# Untested: 128-129 - generic exception catching
