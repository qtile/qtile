from datetime import datetime, timedelta

from libqtile import widget

td = timedelta(days=10, hours=10, minutes=10, seconds=10)


def test_countdown_formatting():
    # Create widget but hide seconds from formatting to allow for
    # timing differences in test environment
    countdown = widget.Countdown(date=datetime.now() + td, format="{D}d {H}h {M}m")

    output = countdown.poll()
    assert output == "10d 10h 10m"
