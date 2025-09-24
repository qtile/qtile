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
