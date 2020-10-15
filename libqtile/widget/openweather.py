# -*- coding:utf-8 -*-
# Copyright (c) 2020 Himanshu Chauhan
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
from urllib.parse import urlencode

from libqtile.widget import base
from libqtile.widget.generic_poll_text import GenPollUrl

# API access details at https://openweathermap.org/current
QUERY_URL = "http://api.openweathermap.org/data/2.5/weather?"


class OpenWeatherResponseError(Exception):
    def __init__(self, resp_code, err_str=None):
        self.resp_code = resp_code
        self.err_str = err_str


class OpenWeatherResponseParser(object):
    def __init__(self, resp_json):
        self.resp_json = resp_json
        self.fjson = self.flatten_json(self.resp_json)
        if int(self.fjson["cod"]) != 200:
            raise OpenWeatherResponseError(int(self.fjson["cod"]))

    def flatten_json(self, obj):
        out = {}

        def __inner(_json, name=''):
            if type(_json) is dict:
                for key, value in _json.items():
                    __inner(value, name + key + '_')
            elif type(_json) is list:
                for i in range(len(_json)):
                    __inner(_json[i], name + str(i) + '_')
            else:
                out[name[:-1]] = _json
        __inner(obj)
        return out

    def get_actual_temperature(self):
        return float(self.fjson["main_temp"])

    def get_feels_like_temperature(self):
        return float(self.fjson["main_feels_like"])

    def get_humidity(self):
        return int(self.fjson["main_humidity"])

    def get_pressure(self):
        return int(self.fjson["main_pressure"])

    def get_visibility(self):
        return int(self.fjson["visibility"])

    def get_wind_speed(self):
        return float(self.fjson["wind_speed"])

    def get_wind_degree(self):
        return int(self.fjson["wind_deg"])

    def get_wind_direction(self):
        val = int((float(self.get_wind_degree()) / 22.5) + .5)
        arr = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE",
               "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW",
               "NNW"]
        return arr[(val % 16)]

    def get_weather_title(self):
        return str(self.fjson["weather_0_main"])

    def get_weather_details(self):
        return str(self.fjson["weather_0_description"])

    def get_sunrise_time(self):
        sr = self.fjson["sys_sunrise"]
        return "{:02d}:{:02d}".format(time.localtime(sr)[3],
                                      time.localtime(sr)[4])

    def get_sunset_time(self):
        sst = self.fjson["sys_sunset"]
        return "{:02d}:{:02d}".format(time.localtime(sst)[3],
                                      time.localtime(sst)[4])

    def get_location_name(self):
        return self.fjson["name"]


class OpenWeather(GenPollUrl):
    """ A weather widget based on Openweather API.

    Format Options:
        - location
        - temp
        - temp_units
        - weather_details
        - sunrise
        - sunset
        - wind_speed
        - wind_speed_units
        - wind_direction
        - humidity
    """
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        (
            'app_key',
            None,
            'Open Weather access key'
        ),
        (
            'woeid',
            None,
            """ID of city. Can be looked up from:
            https://openweathermap.org/find
            Takes precedence over location and coordinates."""
        ),
        (
            'location',
            None,
            """Name of the city. Country name can be appended
            like cambridge,NZ. Takes precedence over coordinates."""
        ),
        (
            'coordinates',
            None,
            """Dictionary containing latitude and longitude
               Example: coordinates={"longitude": "77.22",
                                     "latitude": "28.67"}"""
        ),
        (
            'format',
            '{location}: {temp} {temp_units} {humidity} {weather_details}',
            'Display format'
        ),
        ('metric', True, "True to use metric (Default). Imperial if false"),
        ('language', 'en',
         """Language of response. List of languages supported can
         be seen at: https://openweathermap.org/current under
         Multilingual support""")
    ]

    def __init__(self, **config):
        GenPollUrl.__init__(self, **config)
        self.add_defaults(OpenWeather.defaults)

    @property
    def url(self):
        if not self.app_key and not self.location and not self.coordinates:
            return None

        params = {}
        if self.woeid:
            params['id'] = self.woeid
        elif self.location:
            params['q'] = self.location
        elif self.coordinates:
            params['lat'] = self.coordinates['latitude']
            params['lon'] = self.coordinates['longitude']

        params['appid'] = self.app_key

        if self.metric:
            params['units'] = "metric"
        else:
            params['units'] = "imperial"

        params['lang'] = self.language

        return QUERY_URL + urlencode(params)

    def parse(self, response):
        try:
            opwr = OpenWeatherResponseParser(response)
        except OpenWeatherResponseError as e:
            return "Error {}".format(e.resp_code)

        data = {}
        if self.metric:
            data['temp_units'] = "\u00B0" + "c"
            data['wind_speed_units'] = "kmph"
        else:
            data['temp_units'] = " F"
            data['wind_speed_units'] = "mph"

        data['location'] = opwr.get_location_name()
        data['temp'] = opwr.get_actual_temperature()
        data['humidity'] = str(opwr.get_humidity()) + "%"
        data['weather_details'] = opwr.get_weather_details()
        data['sunrise'] = "\u2600 {}".format(opwr.get_sunrise_time())
        data['sunset'] = "\u26ed {}".format(opwr.get_sunset_time())
        data['weather_concise'] = opwr.get_weather_title()
        data['wind_speed'] = str(opwr.get_wind_speed())
        data['wind_direction'] = opwr.get_wind_direction()

        return self.format.format(**data)
