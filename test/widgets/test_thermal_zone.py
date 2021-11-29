import os.path
from libqtile import widget

def test_thermal_zone_getting_value():
    # If thermal zone zero exists - get value
    zone_zero = '/sys/class/thermal/thermal_zone0/temp'
    zone_exists = os.path.isfile(zone_zero)
    
    if zone_exists:
        thermal_zone = widget.ThermalZone(zone='0')
        output = thermal_zone.poll()
        print(output)
        assert output != ''

