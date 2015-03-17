
# Copyright (c) 2015 Ali Mousavi
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


from . import base
from dbus.mainloop.glib import DBusGMainLoop
import re
import subprocess
import dbus


class KeyboardKbdd(base.InLoopPollText):
    """
        Widget for changing keyboard layouts per window, using kbdd.
        kbdd should be installed and running, you can get it from:
        https://github.com/qnikst/kbdd
    """

    defaults = [
        ("update_interval", 1, "Update time in seconds."),
        ("configured_keyboards", ["us", "ir"],
         "your predefined list of keyboard layouts."
         "example: ['us', 'ir', 'es']"),
        ("colours", None,
         "foreground colour for each layout"
         "either 'None' or a list of colours."
         "example: ['ffffff', 'E6F0AF']. ")
    ]

    def __init__(self, **config):
        base.InLoopPollText.__init__(self, **config)
        self.add_defaults(KeyboardKbdd.defaults)
        self.keyboard = self.configured_keyboards[0]
        if not self._check_kbdd():
            self.keyboard = "N/A"
        self._dbus_init()

    def _check_kbdd(self):
        s = subprocess.Popen(["ps", "axw"], stdout=subprocess.PIPE)
        stdout = s.communicate()[0]
        if re.search("kbdd", stdout):
            return True
        self.log.error('Please, check that kbdd is running')
        return False

    def _dbus_init(self):
        dbus_loop = DBusGMainLoop()
        bus = dbus.SessionBus(mainloop=dbus_loop)
        bus.add_signal_receiver(self._layout_changed,
                                dbus_interface='ru.gentoo.kbdd',
                                signal_name='layoutChanged')

    def _layout_changed(self, layout_changed):
        """
        Hanldler for "layoutChanged" dbus signal.
        """
        if self.colours:
            self._setColour(layout_changed)
        self.keyboard = self.configured_keyboards[layout_changed]

    def _setColour(self, index):
        if isinstance(self.colours, list):
            try:
                self.layout.colour = self.colours[index]
            except ValueError:
                self._setColour(index-1)
        else:
            self.log.error('variable "colours" should be a list, to set a\
                            colour for all layouts, use "foreground".')

    def poll(self):
        return self.keyboard
