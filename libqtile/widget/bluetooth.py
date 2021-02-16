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

from dbus_next.constants import MessageType

from libqtile.log_utils import logger
from libqtile.utils import _send_dbus_message, add_signal_receiver
from libqtile.widget import base


class Bluetooth(base._TextBox):
    """
    Displays bluetooth status or connected device.

    Uses dbus to communicate with the system bus.
    """

    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ('update_interval', 1, 'The update interval.'),
        ('format', '{status}', 'Display format'),
        ('hci', 'dev_XX_XX_XX_XX_XX_XX', 'hci0 device address, can be found with d-feet or similar dbus explorer.')
    ]

    def __init__(self, **config):
        base._TextBox.__init__(self, '', **config)
        self.add_defaults(Bluetooth.defaults)

        self.hci = config['hci']

    async def _config_async(self):
        # get initial device name
        _, device_msg = await _send_dbus_message(session_bus=False,
                                                 message_type=MessageType.METHOD_CALL,
                                                 destination='org.bluez',
                                                 interface='org.freedesktop.DBus.Properties',
                                                 path='/org/bluez/hci0/' + self.hci,
                                                 member='Get',
                                                 signature='ss',
                                                 body=['org.bluez.Device1', 'Name'])
        if device_msg.message_type == MessageType.METHOD_RETURN:
            self.device = device_msg.body[0].value if device_msg.body else ''
        else:
            logger.warning('Failed to get bluetooth device name.')
            self.device = ''

        # get initial connection status
        _, connect_msg = await _send_dbus_message(session_bus=False,
                                                  message_type=MessageType.METHOD_CALL,
                                                  destination='org.bluez',
                                                  interface='org.freedesktop.DBus.Properties',
                                                  path='/org/bluez/hci0/' + self.hci,
                                                  member='Get',
                                                  signature='ss',
                                                  body=['org.bluez.Device1', 'Connected'])
        if connect_msg.message_type == MessageType.METHOD_RETURN:
            self.connected = connect_msg.body[0].value if connect_msg.body else False
        else:
            logger.warning('Failed to get bluetooth connection status.')
            self.connected = False

        # get initial power status
        _, power_msg = await _send_dbus_message(session_bus=False,
                                                message_type=MessageType.METHOD_CALL,
                                                destination='org.bluez',
                                                interface='org.freedesktop.DBus.Properties',
                                                path='/org/bluez/hci0',
                                                member='Get',
                                                signature='ss',
                                                body=['org.bluez.Adapter1', 'Powered'])
        if power_msg.message_type == MessageType.METHOD_RETURN:
            self.powered = power_msg.body[0].value if power_msg.body else False
        else:
            logger.warning('Failed to get bluetooth power status.')
            self.powered = False

        self.update_text()

        # add callbacks for adapter and device
        subscribed_adapter = await add_signal_receiver(self._signal_received_adapter,
                                                       session_bus=False,
                                                       signal_name='PropertiesChanged',
                                                       path='/org/bluez/hci0',
                                                       dbus_interface='org.freedesktop.DBus.Properties')
        if not subscribed_adapter:
            logger.warning('Could not subscribe to bluez adapter.')

        subscribed_device = await add_signal_receiver(self._signal_received_device,
                                                      session_bus=False,
                                                      signal_name='PropertiesChanged',
                                                      path='/org/bluez/hci0/' + self.hci,
                                                      dbus_interface='org.freedesktop.DBus.Properties')
        if not subscribed_device:
            logger.warning('Could not subscribe to bluez device.')

    def _signal_received_adapter(self, message):
        if message.message_type == MessageType.SIGNAL:
            interface_name, changed_properties, invalidated_properties = message.body
            powered = changed_properties.get('Powered', None)
            if powered is not None:
                self.powered = powered.value
                self.update_text()

    def _signal_received_device(self, message):
        logger.warning(message.body)
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
