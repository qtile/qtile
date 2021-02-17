# Copyright (c) 2021 Graeme Holliday
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

from dbus_next.aio import MessageBus
from dbus_next.constants import MessageType, BusType

from libqtile.log_utils import logger
from libqtile.utils import add_signal_receiver
from libqtile.widget import base

BLUEZ = 'org.bluez'
BLUEZ_PATH = '/org/bluez/hci0'
BLUEZ_ADAPTER = 'org.bluez.Adapter1'
BLUEZ_DEVICE = 'org.bluez.Device1'
BLUEZ_PROPERTIES = 'org.freedesktop.DBus.Properties'

class Bluetooth(base._TextBox):
    """
    Displays bluetooth status or connected device.

    Uses dbus to communicate with the system bus.
    """

    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ('update_interval', 1, 'The update interval.'),
        ('format', '{status}', 'Display format'),
        ('hci', '/dev_XX_XX_XX_XX_XX_XX', 'hci0 device path, can be found with d-feet or similar dbus explorer.')
    ]

    def __init__(self, **config):
        base._TextBox.__init__(self, '', **config)
        self.add_defaults(Bluetooth.defaults)

        self.hci = config['hci']

    async def _config_async(self):
        # set initial values
        self.powered = await self._init_adapter()
        self.connected, self.device = await self._init_device()

        self.update_text()

        # add receiver routines for adapter and device
        subscribed_adapter = await add_signal_receiver(self._signal_received_adapter,
                                                       session_bus=False,
                                                       signal_name='PropertiesChanged',
                                                       path=BLUEZ_PATH,
                                                       dbus_interface=BLUEZ_PROPERTIES)
        if not subscribed_adapter:
            logger.warning('Could not subscribe to bluez adapter.')

        subscribed_device = await add_signal_receiver(self._signal_received_device,
                                                      session_bus=False,
                                                      signal_name='PropertiesChanged',
                                                      path=BLUEZ_PATH + self.hci,
                                                      dbus_interface=BLUEZ_PROPERTIES)
        if not subscribed_device:
            logger.warning('Could not subscribe to bluez device.')

    async def _init_adapter(self):
        # set up interface to adapter properties using high-level api
        bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
        introspect = await bus.introspect(BLUEZ, BLUEZ_PATH)
        obj = bus.get_proxy_object(BLUEZ, BLUEZ_PATH, introspect)
        iface = obj.get_interface(BLUEZ_PROPERTIES)

        powered = await iface.call_get(BLUEZ_ADAPTER, 'Powered')
        return powered.value

    async def _init_device(self):
        # set up interface to device properties using high-level api
        bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
        introspect = await bus.introspect(BLUEZ, BLUEZ_PATH + self.hci)
        obj = bus.get_proxy_object(BLUEZ, BLUEZ_PATH + self.hci, introspect)
        iface = obj.get_interface(BLUEZ_PROPERTIES)

        connected = await iface.call_get(BLUEZ_DEVICE, 'Connected')
        name = await iface.call_get(BLUEZ_DEVICE, 'Name')
        return connected.value, name.value

    def _signal_received_adapter(self, message):
        if message.message_type == MessageType.SIGNAL:
            interface_name, changed_properties, invalidated_properties = message.body
            powered = changed_properties.get('Powered', None)
            if powered is not None:
                self.powered = powered.value
                self.update_text()

    def _signal_received_device(self, message):
        if message.message_type == MessageType.SIGNAL:
            interface_name, changed_properties, invalidated_properties = message.body
            connected = changed_properties.get('Connected', None)
            if connected is not None:
                self.connected = connected.value
                self.update_text()

            device = changed_properties.get('Name', None)
            if device is not None:
                self.device = device.value
                self.update_text()

    def update_text(self):
        if not self.powered:
            self.text = 'off'
        else:
            if not self.connected:
                self.text = 'on'
            else:
                self.text = self.device

        self.bar.draw()
