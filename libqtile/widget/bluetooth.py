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

import dbus

from libqtile.log_utils import logger
from libqtile.widget import base

class Bluetooth(base.InLoopPollText):
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
        base.InLoopPollText.__init__(self, **config)
        self.add_defaults(Bluetooth.defaults)

        bus = dbus.SystemBus()
        # set up interface into adapter properties
        adapter = bus.get_object('org.bluez', '/org/bluez/hci0')
        adapter_interface = dbus.Interface(adapter, 'org.bluez.Adapter1')
        self._adapter = dbus.Interface(adapter_interface, 'org.freedesktop.DBus.Properties')
        # set up interface into device properties
        device = bus.get_object('org.bluez', '/org/bluez/hci0/' + config['hci'])
        device_interface = dbus.Interface(device, 'org.bluez.Device1')
        self._device = dbus.Interface(device_interface, 'org.freedesktop.DBus.Properties')

    def poll(self):
        try:
            powered = self._adapter.Get('org.bluez.Adapter1', 'Powered')
            if powered == 0:
                status = 'off'
            else:
                connected = self._device.Get('org.bluez.Device1', 'Connected')
                if connected == 0:
                    status = 'on'
                else:
                    status = self._device.Get('org.bluez.Device1', 'Name')

            return self.format.format(status=status)

        except EnvironmentError:
            logger.error('%s: Make sure your hci0 device has the correct address.', self.__class__.__name__)
