import time

import pytest

from libqtile.widget import open_weather

MOCK_RESPONSE = {
    "coord": {"lon": -0.13, "lat": 51.51},
    "weather": [
        {
            "id": 300,
            "main": "Drizzle",
            "description": "light intensity drizzle",
            "icon": "09d",
        }
    ],
    "base": "stations",
    "main": {
        "temp": 280.15 - 273.15,
        "pressure": 1012,
        "humidity": 81,
        "temp_min": 279.15 - 273.15,
        "temp_max": 281.15 - 273.15,
    },
    "visibility": 10000,
    "wind": {"speed": 4.1, "deg": 80},
    "clouds": {"all": 90},
    "dt": 1485789600,
    "sys": {
        "type": 1,
        "id": 5091,
        "message": 0.0103,
        "country": "GB",
        "sunrise": 1485762037,
        "sunset": 1485794875,
    },
    "id": 2643743,
    "name": "London",
    "cod": 200,
}


@pytest.mark.parametrize(
    "params,expected",
    [
        ({"location": "London"}, "London: 7.0 °C 81% light intensity drizzle"),
        (
            {"location": "London", "format": "{location_city}: {sunrise} {sunset}"},
            "London: 07:40 16:47",
        ),
        (
            {
                "location": "London",
                "format": "{location_city}: {wind_speed} {wind_deg} {wind_direction}",
            },
            "London: 4.1 80 E",
        ),
        ({"location": "London", "format": "{location_city}: {icon}"}, "London: 🌧️"),
    ],
)
def test_openweather_parse(monkeypatch, params, expected):
    """Check widget parses output correctly for display."""
    monkeypatch.setattr("libqtile.widget.open_weather.time.localtime", time.gmtime)

    widget = open_weather.OpenWeather(**params)
    result = widget.parse(MOCK_RESPONSE)
    assert result == expected


@pytest.mark.parametrize(
    "params,vals",
    [
        ({"location": "London"}, ["q=London"]),
        ({"cityid": 2643743}, ["id=2643743"]),
        ({"zip": 90210}, ["zip=90210"]),
        (
            {"coordinates": {"longitude": "77.22", "latitude": "28.67"}},
            ["lat=28.67", "lon=77.22"],
        ),
    ],
)
def test_url(params, vals):
    """Test that url is created correctly."""
    widget = open_weather.OpenWeather(**params)
    url = widget.url
    for val in vals:
        assert val in url
