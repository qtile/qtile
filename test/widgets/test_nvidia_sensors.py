from libqtile.widget.nvidia_sensors import (
    NvidiaSensors,
    _all_sensors_names_correct,
)


def test_nvidia_sensors_input_regex():
    correct_sensors = NvidiaSensors(
        format='temp:{temp}°C,fan{fan_speed}asd,performance{perf}fds'
    )._parse_format_string()
    incorrect_sensors = {'tem', 'fan_speed', 'perf'}
    assert correct_sensors == {'temp', 'fan_speed', 'perf'}
    assert _all_sensors_names_correct(correct_sensors)
    assert not _all_sensors_names_correct(incorrect_sensors)
