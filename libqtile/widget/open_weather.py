# -*- coding:utf-8 -*-
# Copyright (c) 2020 Himanshu Chauhan
# Copyright (c) 2020 Stephan Ehlers
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

import time
from typing import Any
from urllib.parse import urlencode

from libqtile.widget.generic_poll_text import GenPollUrl

# See documentation: https://openweathermap.org/current
QUERY_URL = "http://api.openweathermap.org/data/2.5/weather?"
DEFAULT_APP_ID = "7834197c2338888258f8cb94ae14ef49"


class OpenWeatherResponseError(Exception):
    def __init__(self, resp_code, err_str=None):
        self.resp_code = resp_code
        self.err_str = err_str


def flatten_json(obj):
    out = {}

    def __inner(_json, name=""):
        if type(_json) is dict:
            for key, value in _json.items():
                __inner(value, name + key + "_")
        elif type(_json) is list:
            for i in range(len(_json)):
                __inner(_json[i], name + str(i) + "_")
        else:
            out[name[:-1]] = _json

    __inner(obj)
    return out


def degrees_to_direction(degrees):
    val = int(degrees / 22.5 + 0.5)
    arr = [
        "N",
        "NNE",
        "NE",
        "ENE",
        "E",
        "ESE",
        "SE",
        "SSE",
        "S",
        "SSW",
        "SW",
        "WSW",
        "W",
        "WNW",
        "NW",
        "NNW",
    ]
    return arr[(val % 16)]


class _OpenWeatherResponseParser:
    def __init__(self, response, dateformat, timeformat):
        self.dateformat = dateformat
        self.timeformat = timeformat
        self.data = self._parse(response)
        self._remap(self.data)
        if int(self.data["cod"]) != 200:
            raise OpenWeatherResponseError(int(self.data["cod"]))

    def _parse(self, response):
        return flatten_json(response)

    def _remap(self, data):
        data["location_lat"] = data.get("coord_lat", None)
        data["location_long"] = data.get("coord_lon", None)
        data["location_city"] = data.get("name", None)
        data["location_cityid"] = data.get("id", None)
        data["location_country"] = data.get("sys_country", None)
        data["sunrise"] = self._get_sunrise_time()
        data["sunset"] = self._get_sunset_time()
        data["isotime"] = self._get_dt()
        data["wind_direction"] = self._get_wind_direction()
        data["weather"] = data.get("weather_0_main", None)
        data["weather_details"] = data.get("weather_0_description", None)
        data["humidity"] = data.get("main_humidity", None)
        data["pressure"] = data.get("main_pressure", None)
        data["temp"] = data.get("main_temp", None)

    def _get_wind_direction(self):
        wd = self.data.get("wind_deg", None)
        if wd is None:
            return None
        return degrees_to_direction(wd)

    def _get_sunrise_time(self):
        dt = self.data.get("sys_sunrise", None)
        if dt is None:
            return None
        return time.strftime(self.timeformat, time.localtime(dt))

    def _get_sunset_time(self):
        dt = self.data.get("sys_sunset", None)
        if dt is None:
            return None
        return time.strftime(self.timeformat, time.localtime(dt))

    def _get_dt(self):
        dt = self.data.get("dt", None)
        if dt is None:
            return None
        return time.strftime(self.dateformat + self.timeformat, time.localtime(dt))


class OpenWeather(GenPollUrl):
    """A weather widget, data provided by the OpenWeather API.

    Some format options:
        - location_city
        - location_cityid
        - location_country
        - location_lat
        - location_long

        - weather
        - weather_details
        - units_temperature
        - units_wind_speed
        - isotime
        - humidity
        - pressure
        - sunrise
        - sunset
        - temp
        - visibility
        - wind_speed
        - wind_deg
        - wind_direction

        - main_feels_like
        - main_temp_min
        - main_temp_max
        - clouds_all
        - icon

    Icon support is available but you will need a suitable font installed. A default icon mapping
    is provided (``OpenWeather.symbols``) but changes can be made by setting ``weather_symbols``.
    Available icon codes can be viewed here: https://openweathermap.org/weather-conditions#Icon-list
    """

    symbols = {
        "Unknown": "✨",
        "01d": "☀️",
        "01n": "🌕",
        "02d": "🌤️",
        "02n": "☁️",
        "03d": "🌥️",
        "03n": "☁️",
        "04d": "☁️",
        "04n": "☁️",
        "09d": "🌧️",
        "09n": "🌧️",
        "10d": "⛈",
        "10n": "⛈",
        "11d": "🌩",
        "11n": "🌩",
        "13d": "❄️",
        "13n": "❄️",
        "50d": "🌫",
        "50n": "🌫",
    }

    defaults = [
        # One of (cityid, location, zip, coordinates) must be set.
        (
            "app_key",
            DEFAULT_APP_ID,
            """Open Weather access key. A default is provided, but
            for prolonged use obtaining your own is suggested:
            https://home.openweathermap.org/users/sign_up""",
        ),
        (
            "cityid",
            None,
            """City ID. Can be looked up on e.g.:
            https://openweathermap.org/find
            Takes precedence over location and coordinates.
            Note that this is not equal to a WOEID.""",
        ),
        (
            "location",
            None,
            """Name of the city. Country name can be appended
            like cambridge,NZ. Takes precedence over zip-code.""",
        ),
        (
            "zip",
            None,
            """Zip code (USA) or "zip code,country code" for
            other countries. E.g. 12345,NZ. Takes precedence over
            coordinates.""",
        ),
        (
            "coordinates",
            None,
            """Dictionary containing latitude and longitude
               Example: coordinates={"longitude": "77.22",
                                     "latitude": "28.67"}""",
        ),
        (
            "format",
            "{location_city}: {main_temp} °{units_temperature} {humidity}% {weather_details}",
            "Display format",
        ),
        ("metric", True, "True to use metric/C, False to use imperial/F"),
        (
            "dateformat",
            "%Y-%m-%d ",
            """Format for dates, defaults to ISO.
            For details see: https://docs.python.org/3/library/time.html#time.strftime""",
        ),
        (
            "timeformat",
            "%H:%M",
            """Format for times, defaults to ISO.
            For details see: https://docs.python.org/3/library/time.html#time.strftime""",
        ),
        (
            "language",
            "en",
            """Language of response. List of languages supported can
         be seen at: https://openweathermap.org/current under
         Multilingual support""",
        ),
        (
            "weather_symbols",
            dict(),
            "Dictionary of weather symbols. Can be used to override default symbols.",
        ),
    ]  # type: list[tuple[str, Any, str]]

    def __init__(self, **config):
        GenPollUrl.__init__(self, **config)
        self.add_defaults(OpenWeather.defaults)
        self.symbols.update(self.weather_symbols)

    @property
    def url(self):
        if not self.cityid and not self.location and not self.zip and not self.coordinates:
            return None

        params = {
            "appid": self.app_key or DEFAULT_APP_ID,
            "units": "metric" if self.metric else "imperial",
        }
        if self.cityid:
            params["id"] = self.cityid
        elif self.location:
            params["q"] = self.location
        elif self.zip:
            params["zip"] = self.zip
        elif self.coordinates:
            params["lat"] = self.coordinates["latitude"]
            params["lon"] = self.coordinates["longitude"]

        if self.language:
            params["lang"] = self.language

        return QUERY_URL + urlencode(params)

    def parse(self, response):
        try:
            rp = _OpenWeatherResponseParser(response, self.dateformat, self.timeformat)
        except OpenWeatherResponseError as e:
            return "Error {}".format(e.resp_code)

        data = rp.data
        data["units_temperature"] = "C" if self.metric else "F"
        data["units_wind_speed"] = "Km/h" if self.metric else "m/h"
        data["icon"] = self.symbols.get(data["weather_0_icon"], self.symbols["Unknown"])

        return self.format.format(**data)
