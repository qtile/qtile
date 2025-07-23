import csv
import re

from libqtile.widget import base

sensors_mapping = {
    "fan_speed": "fan.speed",
    "perf": "pstate",
    "temp": "temperature.gpu",
}


def _all_sensors_names_correct(sensors):
    return all(map(lambda x: x in sensors_mapping, sensors))


class NvidiaSensors(base.BackgroundPoll):
    """Displays temperature, fan speed and performance level Nvidia GPU."""

    defaults = [
        (
            "format",
            "{temp}°C",
            "Display string format. Three options available:  "
            "``{temp}`` - temperature, ``{fan_speed}`` and ``{perf}`` - "
            "performance level",
        ),
        ("foreground_alert", "ff0000", "Foreground colour alert"),
        (
            "gpu_bus_id",
            "",
            "GPU's Bus ID, ex: ``01:00.0``. If leave empty will display all available GPU's",
        ),
        ("update_interval", 2, "Update interval in seconds."),
        (
            "threshold",
            70,
            "If the current temperature value is above, then change to foreground_alert colour",
        ),
    ]

    def __init__(self, **config):
        base.BackgroundPoll.__init__(self, "", **config)
        self.add_defaults(NvidiaSensors.defaults)
        self.foreground_normal = self.foreground

    def _get_sensors_data(self, command):
        return csv.reader(
            self.call_process(command, shell=True).strip().replace(" ", "").split("\n")
        )

    def _parse_format_string(self):
        return {sensor for sensor in re.findall("{(.+?)}", self.format)}

    def poll(self):
        sensors = self._parse_format_string()
        if not _all_sensors_names_correct(sensors):
            return "Wrong sensor name"
        bus_id = f"-i {self.gpu_bus_id}" if self.gpu_bus_id else ""
        command = "nvidia-smi {} --query-gpu={} --format=csv,noheader".format(
            bus_id, ",".join(sensors_mapping[sensor] for sensor in sensors)
        )
        try:
            sensors_data = [dict(zip(sensors, gpu)) for gpu in self._get_sensors_data(command)]
            for gpu in sensors_data:
                if gpu.get("temp"):
                    if int(gpu["temp"]) > self.threshold:
                        self.layout.colour = self.foreground_alert
                    else:
                        self.layout.colour = self.foreground_normal
            return " - ".join([self.format.format(**gpu) for gpu in sensors_data])
        except Exception:
            return None
