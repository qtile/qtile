# Copyright (c) 2022 elParaguayo
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
import os
import tempfile
from functools import partial

import pytest

from libqtile.widget import thermal_zone


@pytest.fixture
def widget():
    with tempfile.TemporaryDirectory() as zone_dir:
        zone_file = os.path.join(zone_dir, "temp")
        with open(zone_file, "w") as zone:
            zone.write("49000")
        yield partial(thermal_zone.ThermalZone, zone=zone_file)


@pytest.mark.parametrize(
    "screenshot_manager", [{}, {"high": 45}, {"high": 40, "crit": 45}], indirect=True
)
def ss_thermal_zone(screenshot_manager):
    screenshot_manager.take_screenshot()
