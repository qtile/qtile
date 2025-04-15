# Copyright (c) 2023 elParaguayo
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
import asyncio
import multiprocessing
import os
import shutil
import signal
import subprocess
import time
from enum import Enum

import pytest
from dbus_fast.aio import MessageBus
from dbus_fast.constants import BusType, PropertyAccess
from dbus_fast.service import ServiceInterface, dbus_property, method

from libqtile.bar import Bar
from libqtile.config import Screen
from libqtile.widget.bluetooth import BLUEZ_ADAPTER, BLUEZ_BATTERY, BLUEZ_DEVICE, Bluetooth
from test.conftest import BareConfig
from test.helpers import Retry

ADAPTER_PATH = "/org/bluez/hci0"
ADAPTER_NAME = "qtile_bluez"
BLUEZ_SERVICE = "test.qtile.bluez"


class DeviceState(Enum):
    UNPAIRED = 1
    PAIRED = 2
    CONNECTED = 3


class ForceSessionBusType:
    SESSION = BusType.SESSION
    SYSTEM = BusType.SESSION


class Device(ServiceInterface):
    def __init__(self, *args, alias, state, adapter, address, **kwargs):
        ServiceInterface.__init__(self, *args, **kwargs)
        self._state = state
        self._name = alias
        self._adapter = adapter
        self._address = ":".join([address] * 8)

    @method()
    def Pair(self):  # noqa: F821, N802
        self._state = DeviceState.PAIRED
        self.emit_properties_changed({"Paired": True, "Connected": False})

    @method()
    def Connect(self):  # noqa: F821, N802
        self._state = DeviceState.CONNECTED
        self.emit_properties_changed({"Paired": True, "Connected": True})

    @method()
    def Disconnect(self):  # noqa: F821, N802
        self._state = DeviceState.PAIRED
        self.emit_properties_changed({"Paired": True, "Connected": False})

    @dbus_property(access=PropertyAccess.READ)
    def Name(self) -> "s":  # noqa: F821, N802
        return self._name

    @dbus_property(access=PropertyAccess.READ)
    def Address(self) -> "s":  # noqa: F821, N802
        return self._address

    @dbus_property(access=PropertyAccess.READ)
    def Adapter(self) -> "s":  # noqa: F821, N802
        return self._adapter

    @dbus_property(access=PropertyAccess.READ)
    def Connected(self) -> "b":  # noqa: F821, N802
        return self._state == DeviceState.CONNECTED

    @dbus_property(access=PropertyAccess.READ)
    def Paired(self) -> "b":  # noqa: F821, N802
        return self._state != DeviceState.UNPAIRED


class Adapter(ServiceInterface):
    def __init__(self, *args, **kwargs):
        ServiceInterface.__init__(self, *args, **kwargs)
        self._name = ADAPTER_NAME
        self._powered = True
        self._discovering = False

    @dbus_property(access=PropertyAccess.READ)
    def Name(self) -> "s":  # noqa: F821, N802
        return self._name

    @dbus_property()
    def Powered(self) -> "b":  # noqa: F821, N802
        return self._powered

    @Powered.setter
    def Powered_setter(self, state: "b"):  # noqa: F821, N802
        self._powered = state
        self.emit_properties_changed({"Powered": state})

    @dbus_property(access=PropertyAccess.READ)
    def Discovering(self) -> "b":  # noqa: F821, N802
        return self._discovering

    @method()
    def StartDiscovery(self):  # noqa: F821, N802
        self._discovering = True
        self.emit_properties_changed({"Discovering": self._discovering})

    @method()
    def StopDiscovery(self):  # noqa: F821, N802
        self._discovering = False
        self.emit_properties_changed({"Discovering": self._discovering})


class Battery(ServiceInterface):
    @dbus_property(PropertyAccess.READ)
    def Percentage(self) -> "d":  # noqa: F821, N802
        return 75


class QtileRoot(ServiceInterface):
    def __init__(self):
        super().__init__("org.qtile.root")


class Bluez:
    """Class that runs fake UPower interface."""

    async def start_server(self):
        """Connects to the bus and publishes 3 interfaces."""
        bus = await MessageBus().connect()
        root = QtileRoot()
        bus.export("/", root)

        unpaired_device = Device(
            BLUEZ_DEVICE,
            alias="Earbuds",
            state=DeviceState.UNPAIRED,
            address="11",
            adapter=ADAPTER_PATH,
        )
        paired_device = Device(
            BLUEZ_DEVICE,
            alias="Headphones",
            state=DeviceState.PAIRED,
            address="22",
            adapter=ADAPTER_PATH,
        )
        connected_device = Device(
            BLUEZ_DEVICE,
            alias="Speaker",
            state=DeviceState.CONNECTED,
            address="33",
            adapter=ADAPTER_PATH,
        )
        battery = Battery(BLUEZ_BATTERY)

        for d in [unpaired_device, paired_device, connected_device]:
            path = f"{ADAPTER_PATH}/dev_{d._address.replace(':', '_')}"
            bus.export(path, d)

            if d is connected_device:
                bus.export(path, battery)

        adapter = Adapter(BLUEZ_ADAPTER)
        bus.export(ADAPTER_PATH, adapter)

        # Request the service name
        await bus.request_name(BLUEZ_SERVICE)

        await asyncio.get_event_loop().create_future()

    def run(self):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self.start_server())


@pytest.fixture()
def fake_dbus_daemon(monkeypatch):
    """Start a thread which publishes a fake bluez interface on dbus."""
    # for Github CI/Ubuntu, dbus-launch is provided by "dbus-x11" package
    launcher = shutil.which("dbus-launch")

    # If dbus-launch can't be found then tests will fail so we
    # need to skip
    if launcher is None:
        pytest.skip("dbus-launch must be installed")

    # dbus-launch prints two lines which should be set as
    # environmental variables
    result = subprocess.run(launcher, capture_output=True)

    pid = None
    for line in result.stdout.decode().splitlines():
        # dbus server addresses can have multiple "=" so
        # we use partition to split by the first one onle
        var, _, val = line.partition("=")

        # Use monkeypatch to set these variables so they are
        # removed at end of test.
        monkeypatch.setitem(os.environ, var, val)

        # We want the pid so we can kill the process when the
        # test is finished
        if var == "DBUS_SESSION_BUS_PID":
            try:
                pid = int(val)
            except ValueError:
                pass

    p = multiprocessing.Process(target=Bluez().run)
    p.start()

    # Pause for the dbus interface to come up
    time.sleep(1)

    yield

    # Stop the bus
    if pid:
        os.kill(pid, signal.SIGTERM)
        p.kill()


@pytest.fixture
def widget(monkeypatch):
    """Patch the widget to use the fake dbus service."""
    monkeypatch.setattr("libqtile.widget.bluetooth.BLUEZ_SERVICE", BLUEZ_SERVICE)
    # Make dbus_fast always return the session bus address even if system bus is requested
    monkeypatch.setattr("libqtile.widget.bluetooth.BusType", ForceSessionBusType)

    yield Bluetooth


@pytest.fixture
def bluetooth_manager(request, widget, fake_dbus_daemon, manager_nospawn):
    class BluetoothConfig(BareConfig):
        screens = [Screen(top=Bar([widget(**getattr(request, "param", dict()))], 20))]

    manager_nospawn.start(BluetoothConfig)

    yield manager_nospawn


@Retry(ignore_exceptions=(AssertionError,))
def wait_for_text(widget, text):
    assert widget.info()["text"] == text


def test_defaults(bluetooth_manager):
    widget = bluetooth_manager.c.widget["bluetooth"]

    def text():
        return widget.info()["text"]

    def click():
        bluetooth_manager.c.bar["top"].fake_button_press(0, 0, 1)

    # Show prefix plus list of connected devices (1 connected at startup)
    wait_for_text(widget, "BT Speaker")

    widget.scroll_up()
    assert text() == f"Adapter: {ADAPTER_NAME} [*]"

    widget.scroll_up()
    assert text() == "Device: Earbuds [?]"

    widget.scroll_up()
    assert text() == "Device: Headphones [-]"

    widget.scroll_up()
    assert text() == "Device: Speaker (75.0%) [*]"

    widget.scroll_up()
    assert text() == "BT Speaker"

    widget.scroll_down()
    widget.scroll_down()
    assert text() == "Device: Headphones [-]"


def test_device_actions(bluetooth_manager):
    widget = bluetooth_manager.c.widget["bluetooth"]

    def text():
        return widget.info()["text"]

    def click():
        bluetooth_manager.c.bar["top"].fake_button_press(0, 0, 1)

    wait_for_text(widget, "BT Speaker")
    widget.scroll_down()
    widget.scroll_down()
    wait_for_text(widget, "Device: Headphones [-]")

    # Clicking a paired device connects it
    click()
    wait_for_text(widget, "Device: Headphones [*]")

    # Clicking a connected device disconnects it
    click()
    wait_for_text(widget, "Device: Headphones [-]")

    # We want it connected for the last check
    click()

    # Clicking an unpaired device pairs and connects it
    widget.scroll_down()
    click()
    wait_for_text(widget, "Device: Earbuds [*]")

    # Clicking this now disconnects it but it remains paired
    click()
    wait_for_text(widget, "Device: Earbuds [-]")

    widget.scroll_down()
    widget.scroll_down()
    # 2 devices are now connected
    assert text() == "BT Headphones, Speaker"


def test_adapter_actions(bluetooth_manager):
    widget = bluetooth_manager.c.widget["bluetooth"]

    def text():
        return widget.info()["text"]

    def click():
        bluetooth_manager.c.bar["top"].fake_button_press(0, 0, 1)

    wait_for_text(widget, "BT Speaker")

    widget.scroll_up()
    assert text() == f"Adapter: {ADAPTER_NAME} [*]"

    click()
    wait_for_text(widget, "Turn power off")

    click()
    wait_for_text(widget, "Turn power on")

    widget.scroll_up()
    assert text() == "Turn discovery on"

    click()
    wait_for_text(widget, "Turn discovery off")

    click()
    wait_for_text(widget, "Turn discovery on")

    widget.scroll_up()
    assert text() == "Exit"

    click()
    # Adapter power is now off
    wait_for_text(widget, f"Adapter: {ADAPTER_NAME} [-]")


@pytest.mark.parametrize(
    "bluetooth_manager",
    [
        {
            "symbol_connected": "C",
            "symbol_paired": "P",
            "symbol_unknown": "U",
            "symbol_powered": ("ON", "OFF"),
        }
    ],
    indirect=True,
)
def test_custom_symbols(bluetooth_manager):
    widget = bluetooth_manager.c.widget["bluetooth"]

    def text():
        return widget.info()["text"]

    def click():
        bluetooth_manager.c.bar["top"].fake_button_press(0, 0, 1)

    wait_for_text(widget, "BT Speaker")

    widget.scroll_up()
    assert text() == f"Adapter: {ADAPTER_NAME} [ON]"

    click()
    wait_for_text(widget, "Turn power off")
    click()
    widget.scroll_up()
    widget.scroll_up()
    click()
    wait_for_text(widget, f"Adapter: {ADAPTER_NAME} [OFF]")

    widget.scroll_up()
    assert text() == "Device: Earbuds [U]"

    widget.scroll_up()
    assert text() == "Device: Headphones [P]"

    widget.scroll_up()
    assert text() == "Device: Speaker (75.0%) [C]"


@pytest.mark.parametrize("bluetooth_manager", [{"default_show_battery": True}], indirect=True)
def test_default_show_battery(bluetooth_manager):
    widget = bluetooth_manager.c.widget["bluetooth"]
    wait_for_text(widget, "BT Speaker (75.0%)")


@pytest.mark.parametrize(
    "bluetooth_manager", [{"adapter_paths": ["/org/bluez/hci1"]}], indirect=True
)
def test_missing_adapter(bluetooth_manager):
    widget = bluetooth_manager.c.widget["bluetooth"]

    def text():
        return widget.info()["text"]

    wait_for_text(widget, "BT ")

    # No adapter or devices should be listed
    widget.scroll_up()
    assert text() == "BT "


@pytest.mark.parametrize(
    "bluetooth_manager",
    [
        {
            "default_text": "BT {connected_devices} {num_connected_devices} {adapters} {num_adapters}"
        }
    ],
    indirect=True,
)
def test_default_text(bluetooth_manager):
    widget = bluetooth_manager.c.widget["bluetooth"]
    wait_for_text(widget, "BT Speaker 1 qtile_bluez 1")


@pytest.mark.parametrize(
    "bluetooth_manager",
    [
        {"device": "/dev_22_22_22_22_22_22_22_22"},
    ],
    indirect=True,
)
def test_default_device(bluetooth_manager):
    widget = bluetooth_manager.c.widget["bluetooth"]
    wait_for_text(widget, "Device: Headphones [-]")
