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
import contextlib
from enum import Enum

from dbus_fast.aio import MessageBus
from dbus_fast.constants import BusType
from dbus_fast.errors import DBusError, InterfaceNotFoundError

from libqtile.command.base import expose_command
from libqtile.log_utils import logger
from libqtile.utils import create_task
from libqtile.widget import base

BLUEZ_SERVICE = "org.bluez"
BLUEZ_DEVICE = "org.bluez.Device1"
BLUEZ_ADAPTER = "org.bluez.Adapter1"
BLUEZ_BATTERY = "org.bluez.Battery1"
OBJECT_MANAGER_INTERFACE = "org.freedesktop.DBus.ObjectManager"
PROPERTIES_INTERFACE = "org.freedesktop.DBus.Properties"


def _catch_dbus_error(msg):
    """Decorator to catch DBusErrors and log a message."""

    def _wrapper(func):
        async def f(self):
            try:
                await func(self)
            except DBusError:
                logger.warning(msg, self.name)

        return f

    return _wrapper


class DeviceState(Enum):
    CONNECTED = 0
    PAIRED = 1
    UNPAIRED = 2


class _BluetoothBase:
    """Base class with some common requirements for devices and adapters."""

    def __init__(self, path, interface, properties_interface, widget):
        self.path = path
        self.interface = interface
        self.widget = widget
        self.properties = properties_interface
        self.properties.on_properties_changed(self.properties_changed)
        self._name = ""

    def __repr__(self):
        """Neater repr to help debugging."""
        return f"<{self.__class__.__name__}: {self.name} ({self.path})>"

    def __del__(self):
        """Remove signal listener when garbage collected."""
        with contextlib.suppress(RuntimeError):
            self.properties.off_properties_changed(self.properties_changed)

    def properties_changed(self, _interface_name, _changed_properties, _invalidated_properties):
        """Handler for properties_changed signal."""
        create_task(self.update_props())

    async def update_props(self):
        raise NotImplementedError


class BluetoothDevice(_BluetoothBase):
    """
    Helper class to represent an org.bluez.Device1 object.

    Exposes basic properties/methods and also listens to signals to
    update properties as needed.
    """

    def __init__(self, path, interface, properties_interface, widget):
        _BluetoothBase.__init__(self, path, interface, properties_interface, widget)
        self._connected = False
        self._paired = False
        self._status = DeviceState.UNPAIRED
        self._adapter = ""
        self.has_name = False
        self.battery_device = None
        self._battery = 0

    @_catch_dbus_error("Unable to connect to device: %s.")
    async def connect(self):
        await self.interface.call_connect()

    @_catch_dbus_error("Unable to disconnect device: %s.")
    async def disconnect(self):
        await self.interface.call_disconnect()

    @_catch_dbus_error("Unable to pair device: %s.")
    async def pair_and_connect(self):
        await self.interface.call_pair()
        await self.connect()

    async def action(self):
        """Helper method to call appropriate method based on device status."""
        if self.connected:
            await self.disconnect()
        elif self.paired and not self.connected:
            await self.connect()
        elif not self.paired:
            await self.pair_and_connect()

    @property
    def name(self):
        return self._name

    @property
    def connected(self):
        return self._connected

    @property
    def paired(self):
        return self._paired

    @property
    def status(self):
        return self._status

    @property
    def battery(self):
        if self.battery_device:
            return self._battery
        return ""

    @property
    def adapter(self):
        a = self.widget.adapters.get(self._adapter)
        if a:
            return a.name
        else:
            return "Unknown"

    def add_battery(self):
        """Triggers adding battery interface."""

        def refresh(_):
            if self.battery_device:
                create_task(self.update_props())

        task = create_task(self.get_battery())
        task.add_done_callback(refresh)

    def remove_battery(self):
        self.battery_device = None
        self._battery = 0

    async def get_battery(self):
        proxy = await self.widget.get_proxy(self.path)
        with contextlib.suppress(InterfaceNotFoundError):
            self.battery_device = proxy.get_interface(BLUEZ_BATTERY)

    async def update_props(self, setup=False):
        """Refresh all the properties for the device."""
        # Some devices don't report a name so we fall back to the device address
        try:
            self._name = await self.interface.get_name()
            self.has_name = True
        except (AttributeError, DBusError):
            self._name = await self.interface.get_address()
            self.has_name = False

        self._connected, self._paired, self._adapter = await asyncio.gather(
            self.interface.get_connected(),
            self.interface.get_paired(),
            self.interface.get_adapter(),
        )

        # If we're setting up, let's see if a battery device is available
        # This may happen if the device is already connected when the widget starts
        if setup:
            await self.get_battery()

        if self.battery_device:
            self._battery = await self.battery_device.get_percentage()

        if self._connected:
            self._status = DeviceState.CONNECTED
        elif self._paired and not self._connected:
            self._status = DeviceState.PAIRED
        else:
            self._status = DeviceState.UNPAIRED

        if not setup:
            self.widget.refresh()

    async def check(self):
        """Checks if device belongs to requested adapter."""
        await self.update_props(setup=True)

        if not self.widget.adapter_paths:
            return True, self

        for path in self.widget.adapter_paths:
            if path == self._adapter:
                return True, self

        return False, self


class BluetoothAdapter(_BluetoothBase):
    """
    Helper class for Bluetooth adapters.

    Exposes basic properties/methods and also listens to signals to
    update properties as needed.
    """

    def __init__(self, path, interface, properties_interface, widget):
        _BluetoothBase.__init__(self, path, interface, properties_interface, widget)
        self._discovering = False
        self._powered = False
        create_task(self.update_props(setup=True))

    @_catch_dbus_error("Unable to start discovery on adapter: %s.")
    async def start_discovery(self):
        await self.interface.call_start_discovery()

    @_catch_dbus_error("Unable to stop discovery on adapter: %s.")
    async def stop_discovery(self):
        await self.interface.call_stop_discovery()

    @_catch_dbus_error("Unable to set power state for adapter: %s.")
    async def power(self):
        await self.interface.set_powered(not self._powered)

    @property
    def discovering(self):
        return self._discovering

    @property
    def powered(self):
        return self._powered

    @property
    def name(self):
        return self._name

    async def discover(self):
        if self.discovering:
            await self.stop_discovery()
        else:
            await self.start_discovery()

    async def update_props(self, setup=False):
        self._discovering = await self.interface.get_discovering()
        self._powered = await self.interface.get_powered()
        self._name = await self.interface.get_name()

        if not setup:
            self.widget.refresh()


class Bluetooth(base._TextBox, base.MarginMixin):
    """
    Bluetooth widget that provides following functionality:
    - View multiple adapters/devices (adapters can be filtered)
    - Set power and discovery status for adapters
    - Connect/disconnect/pair devices

    The widget works by providing a menu in the bar. Different items are accessed
    by scrolling up and down on the widget.

    Clicking on an adapter will open a submenu allowing you to set power and discovery status.

    Clicking on a device will perform an action based on the status of that device:
    - Connected devices will be disconnected
    - Disconnected devices will be connected
    - Unpaired devices (which appear if discovery is on) will be paired and connected

    Symbols are used to show the status of adapters and devices.

    Battery level for bluetooth devices can also be shown if available. This functionality is not available
    by default on all distros. If it doesn't work, you can try adding ``Experimental = true`` to
    ``/etc/bluetooth/main.conf``.
    """

    defaults = [
        ("hide_unnamed_devices", False, "Devices with no name will be hidden from scan results"),
        ("symbol_connected", "*", "Symbol to indicate device is connected"),
        ("symbol_paired", "-", "Symbol to indicate device is paired but unconnected"),
        ("symbol_unknown", "?", "Symbol to indicate device is unpaired"),
        ("symbol_powered", ("*", "-"), "Symbols when adapter is powered and unpowered."),
        (
            "symbol_discovery",
            ("D", ""),
            "Symbols when adapter is discovering and not discovering",
        ),
        (
            "device_format",
            "Device: {name}{battery_level} [{symbol}]",
            "Text to display when showing bluetooth device. "
            "The ``{adapter`` field is also available if you're using multiple adapters.",
        ),
        (
            "device_battery_format",
            " ({battery}%)",
            "Text to be shown if device reports battery level",
        ),
        (
            "adapter_format",
            "Adapter: {name} [{powered}{discovery}]",
            "Text to display when showing adapter device.",
        ),
        (
            "adapter_paths",
            [],
            "List of DBus object path for bluetooth adapter (e.g. '/org/bluez/hci0'). "
            "Empty list will show all adapters.",
        ),
        (
            "default_text",
            "BT {connected_devices}",
            "Text to show when not scrolling through menu. "
            "Available fields: 'connected_devices' list of connected devices, "
            "'num_connected_devices' number of connected devices, "
            "'adapters' list of bluetooth adapters, 'num_adapters' number of bluetooth adapters.",
        ),
        (
            "default_show_battery",
            False,
            "Include battery level of 'connected_devices' in 'default_text'. Uses 'device_battery_format'.",
        ),
        ("separator", ", ", "Separator for lists in 'default_text'."),
        (
            "default_timeout",
            None,
            "Time before reverting to default_text. If 'None', text will stay on selected item.",
        ),
        (
            "device",
            None,
            "Device path, can be found with d-feet or similar dbus explorer. "
            "When set, the widget will default to showing this device status.",
        ),
    ]

    def __init__(self, **config):
        base._TextBox.__init__(self, **config)
        self.add_defaults(Bluetooth.defaults)
        self.add_defaults(base.MarginMixin.defaults)
        self.connected = False
        self.bus = None
        self.devices = {}
        self.adapters = {}
        self._lines = []
        self._line_index = 0
        self._adapter_index = 0
        self._setting_up = True
        self.show_adapter = False
        self.device_found = False
        self.add_callbacks(
            {"Button1": self.click, "Button4": self.scroll_up, "Button5": self.scroll_down}
        )
        self.timer = None
        self.object_manager = None

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        self.symbols = (self.symbol_connected, self.symbol_paired, self.symbol_unknown)

    async def _config_async(self):
        await self._connect()

    async def _connect(self):
        """Connect to bus and set up key listeners."""
        self.bus = await MessageBus(bus_type=BusType.SYSTEM).connect()

        # Get the object manager
        proxy = await self.get_proxy("/")
        self.object_manager = proxy.get_interface(OBJECT_MANAGER_INTERFACE)

        # Subscribe to signals for new and removed interfaces
        self.object_manager.on_interfaces_added(self._interface_added)
        self.object_manager.on_interfaces_removed(self._interface_removed)

        await self._get_managed_objects()

        self.refresh()

    async def get_proxy(self, path):
        """Provides proxy object after introspecting the given path."""
        device_introspection = await self.bus.introspect(BLUEZ_SERVICE, path)
        proxy = self.bus.get_proxy_object(BLUEZ_SERVICE, path, device_introspection)
        return proxy

    async def _get_managed_objects(self):
        """
        Retrieve list of managed objects.

        These are devices that have previously been paired but may or may
        not currently be connected.

        Additionally, if the device is scanning, available objects will also
        appear here, albeit temporarily.
        """
        self._setting_up = True

        objects = await self.object_manager.call_get_managed_objects()

        for path, interfaces in objects.items():
            self._interface_added(path, interfaces)

        self._setting_up = False

    def _interface_added(self, path, interfaces):
        """Handles the object based on the interface type."""
        task = None

        # Create device or adapter
        for device_type in (BLUEZ_DEVICE, BLUEZ_ADAPTER):
            if device_type in interfaces:
                task = create_task(self._add_object(path, device_type))
                break

        if task is not None and not self._setting_up:
            task.add_done_callback(lambda *args: self.refresh())

        # Battery interface is added after the device is connected
        # so no task will have been created at this point.
        if not task and BLUEZ_BATTERY in interfaces:
            if device := self.devices.get(path):
                # Get device to load battery interface
                device.add_battery()

    def _interface_removed(self, path, interfaces):
        # Object has been removed so remove from our list of available devices
        updated = False

        if BLUEZ_DEVICE in interfaces:
            with contextlib.suppress(KeyError):
                del self.devices[path]
                updated = True

        elif BLUEZ_ADAPTER in interfaces:
            with contextlib.suppress(KeyError):
                del self.adapters[path]
                updated = True

        elif BLUEZ_BATTERY in interfaces:
            device = self.devices.get(path)
            if device:
                device.remove_battery()

        if updated and not self._setting_up:
            self.refresh()

    async def _add_object(self, path, device_type):
        proxy = await self.get_proxy(path)

        # Check if object is a valid bluetooth device and ignore it if not
        try:
            interface = proxy.get_interface(device_type)
        except InterfaceNotFoundError:
            return
        # Get the properties interface so we can listed to signals
        properties = proxy.get_interface(PROPERTIES_INTERFACE)

        # Create an object to represent this device and add to our list
        if device_type == BLUEZ_DEVICE:
            # The device will be added to self.devices as part of the __init__
            # process after checking whether we need to filter out the device
            # if it's connected to an unwatched adapter
            # This is preferable to substring matching on 'path' which could
            # result in false positives (in very rare situations)
            device = BluetoothDevice(path, interface, properties, self)
            task = create_task(device.check())
            task.add_done_callback(self._add_device)
        elif device_type == BLUEZ_ADAPTER:
            if not self.adapter_paths or path in self.adapter_paths:
                adapter = BluetoothAdapter(path, interface, properties, self)
                self.adapters[path] = adapter

    def _add_device(self, task):
        success, device = task.result()
        if success:
            self.devices[device.path] = device
            self.refresh()

    def refresh(self):
        if self._setting_up:
            return

        # Store lines in a variable as we'll need to access them elsewhere
        # Each entry is a tuple of (display text, callable)
        self._lines = []

        # If we've clicked on an adapter then we're just showing the adapter submenu
        if self.show_adapter:
            self._lines.extend(self._get_adapter_menu(self._shown_adapter))

        # Otherwise we're in default behavior
        else:
            # Line 1 is the text to be formatted according to "default_text"
            connected = [d for d in self.devices.values() if d.connected]
            adapters = [a.name for a in self.adapters.values()]
            if self.default_show_battery:
                connected_devices = [
                    "{name}{battery}".format(
                        name=d.name,
                        battery=self.device_battery_format.format(battery=d.battery)
                        if d.battery
                        else "",
                    )
                    for d in connected
                ]
            else:
                connected_devices = [d.name for d in connected]
            self._lines.append(
                (
                    self.default_text.format(
                        connected_devices=self.separator.join(connected_devices),
                        num_connected_devices=len(connected_devices),
                        adapters=self.separator.join(adapters),
                        num_adapters=len(adapters),
                    ),
                    lambda: None,
                )
            )

            # Next is the adapters...
            def show(adapter):
                """Function to trigger the adapter submenu."""
                self.show_adapter = True
                self._shown_adapter = adapter
                # Store the current menu position
                self._adapter_index = self._line_index
                # Change menu position to the first item in the submenu
                self._line_index = 0
                self.refresh()

            for adapter in self.adapters.values():
                self._lines.append((adapter, lambda a=adapter: show(a)))

            # Finally, loop over all the devices
            for device in self.devices.values():
                self._lines.append((device, lambda d=device: create_task(d.action())))

        if self._lines:
            # If user has set default device, check if it should be shown
            # This will only force the display to that widget the first time the device is found
            # i.e. once user has scrolled to a different device, it will no longer return to the
            # set device.
            if not self.device_found and self.device is not None:
                for i, (obj, _) in enumerate(self._lines):
                    if isinstance(obj, BluetoothDevice):
                        if self.device in obj.path:
                            self._line_index = i
                            self.device_found = True
                            break

            self.show_line()
        else:
            self.update("")

    def _get_adapter_menu(self, adapter):
        """Builds a submenu for the selected adapter."""
        state = "off" if adapter.powered else "on"
        discovery = "off" if adapter.discovering else "on"

        def exit():
            self.show_adapter = False
            # Restore menu position
            self._line_index = self._adapter_index
            self.refresh()

        return [
            (f"Turn power {state}", lambda a=adapter: create_task(a.power())),
            (f"Turn discovery {discovery}", lambda a=adapter: create_task(a.discover())),
            ("Exit", lambda: exit()),
        ]

    def show_line(self):
        """Formats the text of the current menu item."""
        if not self._lines:
            return

        obj = None

        # If devices disappear we may have an invalid line index
        while obj is None:
            try:
                obj, action = self._lines[self._line_index]
            except IndexError:
                self._line_index -= 1

        self.update(self.format_object(obj))

    def format_object(self, obj):
        """Takes the given object and returns a formatted string representing the object."""
        if isinstance(obj, BluetoothDevice):
            # status.value is 0 for connected, 1 for paired (and unconnected), 2 for unpaired
            symbol = self.symbols[obj.status.value]
            if obj.battery:
                battery_level = self.device_battery_format.format(battery=obj.battery)
            else:
                battery_level = ""
            return self.device_format.format(
                symbol=symbol, name=obj.name, adapter=obj.adapter, battery_level=battery_level
            )

        elif isinstance(obj, BluetoothAdapter):
            powered = 0 if obj.powered else 1
            discovery = 0 if obj.discovering else 1
            return self.adapter_format.format(
                powered=self.symbol_powered[powered],
                discovery=self.symbol_discovery[discovery],
                name=obj.name,
            )

        elif isinstance(obj, str):
            return obj

        # Shouldn't happen but let's be safe!
        return ""

    @expose_command
    def scroll_up(self):
        """Scroll up to next item."""
        self._scroll(1)

    @expose_command
    def scroll_down(self):
        """Scroll down to next item."""
        self._scroll(-1)

    @expose_command
    def click(self):
        """Perform default action on visible item."""
        with contextlib.suppress(IndexError):
            _, action = self._lines[self._line_index]
            action()

    def _scroll(self, step):
        if self.timer is not None:
            self.timer.cancel()

        if self._lines:
            self._line_index = (self._line_index + step) % len(self._lines)
            self.show_line()

        if self.default_timeout is not None:
            self.timer = self.timeout_add(self.default_timeout, self.hide)

    def hide(self):
        """Revert widget contents to default."""
        self._line_index = 0
        self.show_adapter = False
        self.refresh()

    def finalize(self):
        # if we failed to connect, there is nothing to finalize.
        if self.bus is None:
            return

        # Remove dbus signal handlers before finalising.
        # Clearing dicts will call the __del__ method on the stored objects
        # which has been defined to remove signal handlers
        self.devices.clear()
        self.adapters.clear()

        # Remove object manager's handlers
        if self.object_manager is not None:
            self.object_manager.off_interfaces_added(self._interface_added)
            self.object_manager.off_interfaces_removed(self._interface_removed)

        # Disconnect the bus connection
        self.bus.disconnect()
        self.bus = None

        base._TextBox.finalize(self)
