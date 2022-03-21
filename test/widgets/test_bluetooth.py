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
from dbus_next import Variant

import libqtile.config
import libqtile.widget.bluetooth
from libqtile.bar import Bar
from libqtile.config import Screen


class MockProps:
    def on_properties_changed(self, callback):
        pass


class MockDevice:
    async def get_name(self):
        return "Mock Bluetooth Device"

    async def get_connected(self):
        return True


class MockAdapter:
    async def get_powered(self):
        return True


class MockProxy:
    def get_interface(self, interface):
        if interface == libqtile.widget.bluetooth.BLUEZ_ADAPTER:
            return MockAdapter()
        elif interface == libqtile.widget.bluetooth.BLUEZ_DEVICE:
            return MockDevice()
        else:
            return MockProps()


class MockBus:
    async def introspect(self, service, path):
        return None

    def get_proxy_object(self, service, path, introspection):
        return MockProxy()


class MockMessageBus:
    def __init__(self, bus_type=None):
        pass

    async def connect(self):
        return MockBus()


def test_bluetooth_setup(monkeypatch, minimal_conf_noscreen, manager_nospawn):
    monkeypatch.setattr("libqtile.widget.bluetooth.MessageBus", MockMessageBus)
    widget = libqtile.widget.bluetooth.Bluetooth()
    config = minimal_conf_noscreen
    config.screens = [Screen(top=Bar([widget], 10))]
    manager_nospawn.start(config)

    text = manager_nospawn.c.widget["bluetooth"].info()["text"]
    assert text == "Mock Bluetooth Device"


def test_signal_handling(monkeypatch):
    def new_update(self, text):
        self.text = text

    monkeypatch.setattr("libqtile.widget.bluetooth.Bluetooth.update", new_update)
    widget = libqtile.widget.bluetooth.Bluetooth()
    widget.connected = True
    widget.device = "Mock Bluetooth Device"
    widget.powered = True

    widget.update_text()
    assert widget.text == "Mock Bluetooth Device"

    widget._signal_received(None, {"Name": Variant("s", "New Device Name")}, None)
    assert widget.text == "New Device Name"

    widget._signal_received(None, {"Connected": Variant("b", False)}, None)
    assert widget.text == "on"

    widget._signal_received(None, {"Powered": Variant("b", False)}, None)
    assert widget.text == "off"
