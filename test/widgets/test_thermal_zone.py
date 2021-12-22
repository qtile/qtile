import os

from libqtile import widget


def test_thermal_zone_getting_value():
    # Create temporary zone file
    tmp = "/var/tmp/qtile/test/widgets/thermal_zone"
    zone_file = tmp + "/sys/class/thermal/thermal_zone0/temp"
    os.makedirs(os.path.dirname(zone_file), exist_ok=True)

    class FakeLayout:
        pass

    with open(zone_file, "w") as f:
        f.write("22000")

    thermal_zone = widget.ThermalZone(zone=zone_file)
    thermal_zone.layout = FakeLayout()
    output = thermal_zone.poll()
    assert output == "22°C"
