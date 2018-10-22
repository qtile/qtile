# -*- coding: utf-8 -*-
# Copyright (C) 2018 Juan Riquelme González
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from . import base

import re
import subprocess


class CapsNumLockIndicator(base.ThreadPoolText):
    """Really simple widget to show the current Caps/Num Lock state."""

    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [('update_interval', 0.5, 'Update Time in seconds.')]

    def __init__(self, **config):
        base.ThreadPoolText.__init__(self, "", **config)
        self.add_defaults(CapsNumLockIndicator.defaults)

    def get_indicators(self):
        """Return a list with the current state of the keys."""
        try:
            output = self.call_process(['xset', 'q'])
        except subprocess.CalledProcessError as err:
            output = err.output.decode()
        if output.startswith("Keyboard"):
            indicators = re.findall(r"(Caps|Num)\s+Lock:\s*(\w*)", output)
            return indicators

    def status(self):
        """Return a string with the Caps Lock/Num Lock status."""
        indicators = self.get_indicators()
        status = " ".join([" ".join(indicator) for indicator in indicators])
        return status

    def poll(self):
        """Poll content for the text box."""
        return self.status()
