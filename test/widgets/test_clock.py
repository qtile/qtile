import datetime
import time

import pytest

from libqtile.widget import clock


class MockDatetime(datetime.datetime):
    @classmethod
    def now(cls, tz=None, *args, **kwargs):
        return cls(2021, 1, 1, 10, 20, 30, tzinfo=tz)


@pytest.fixture
def patched_clock(monkeypatch):
    # Pretend the system timezone is UTC so .astimezone() with no arg behaves
    # consistently across test machines.
    monkeypatch.setenv("TZ", "UTC")
    time.tzset()
    monkeypatch.setattr("libqtile.widget.clock.datetime", MockDatetime)


@pytest.mark.usefixtures("patched_clock")
def test_clock_default():
    """test clock output with default settings"""
    assert clock.Clock().poll() == "10:20"


@pytest.mark.usefixtures("patched_clock")
def test_clock_invalid_timezone(caplog):
    """test clock widget with invalid timezone string"""
    clock.Clock(timezone="Not/A/Real/Zone")
    assert "Invalid timezone Not/A/Real/Zone." in caplog.text


@pytest.mark.usefixtures("patched_clock")
def test_clock_datetime_timezone():
    """test clock with a datetime.tzinfo timezone"""
    tz = datetime.timezone(datetime.timedelta(hours=1))
    assert clock.Clock(timezone=tz).poll() == "11:20"


@pytest.mark.usefixtures("patched_clock")
def test_clock_string_timezone():
    """test clock with a zoneinfo string timezone"""
    # Asia/Kolkata is UTC+5:30 year-round (no DST)
    assert clock.Clock(timezone="Asia/Kolkata").poll() == "15:50"


@pytest.mark.usefixtures("patched_clock")
def test_clock_change_timezones():
    """test commands to change timezones"""
    tz1 = datetime.timezone(datetime.timedelta(hours=1))
    tz2 = datetime.timezone(-datetime.timedelta(hours=1))

    clk = clock.Clock(timezone=tz1)
    assert clk.poll() == "11:20"

    clk.timezone = clk._lift_timezone(tz2)
    assert clk.poll() == "09:20"

    clk.timezone = clk._lift_timezone("")
    assert clk.poll() == "10:20"
