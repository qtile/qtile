# -*- coding:utf-8 -*-
# Copyright (c) 2011-2012 dmpayton
# Copyright (c) 2011 Kenji_Takahashi
# Copyright (c) 2011 Mounier Florian
# Copyright (c) 2012, 2014-2015 Tycho Andersen
# Copyright (c) 2013 David R. Andersen
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2014 Sean Vig
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
import uuid
from urllib.parse import urlencode

from libqtile.widget import base
from libqtile.widget.generic_poll_text import GenPollUrl

# See documentation: https://developer.yahoo.com/weather/documentation.html
QUERY_URL = 'https://weather-ydn-yql.media.yahoo.com/forecastrss?'
APP_ID = 'xSqyTW54'
CONSUMER_KEY = ('dj0yJmk9R0RwZ3dveWEwTHdWJmQ9WVdrOWVGTnhlVlJYTlRRb'
                'WNHbzlNQS0tJnM9Y29uc3VtZXJzZWNyZXQmc3Y9MCZ4PTVi')
CONSUMER_SECRET = '83ea8fbd202ea06cd57fc01268139601bf966b47'
HEADER = {'X-Yahoo-App-Id': APP_ID}


class _YahooWeatherResponseParser(base._WeatherResponseParser):
    def __init__(self, response, dateformat, timeformat):
        self.dateformat = dateformat
        self.timeformat = timeformat
        base._WeatherResponseParser.__init__(self, response)

    def _parse(self, response):
        return base._WeatherResponseParser.flatten_json(response)

    def _remap(self, data):
        data['weather'] = data.get('current_observation_condition_text', None)
        data['weather_details'] = data['weather']
        data['wind_deg'] = data.get('current_observation_wind_direction', None)
        data['wind_direction'] = self._get_wind_direction()
        data['wind_speed'] = data.get('current_observation_wind_speed', None)
        data['humidity'] = data.get('current_observation_atmosphere_humidity', None)
        data['visibility'] = data.get('current_observation_atmosphere_visibility', None)
        data['pressure'] = data.get('current_observation_atmosphere_pressure', None)
        data['sunrise'] = self._get_sunrise_time()
        data['sunset'] = self._get_sunset_time()
        data['temp'] = data.get('current_observation_condition_temperature', None)
        data['isotime'] = self._get_dt()

        # symbols: https://unicode-search.net/unicode-namesearch.pl?term=RAIN
        condition_mapping = {
            0: '🌪',  # tornado
            #  1: '',  # tropical storm
            #  2: '',  # hurricane
            3: '⛈',  # severe thunderstorms
            4: '⛈',  # thunderstorms
            #  5: '',  # mixed rain and snow
            #  6: '',  # mixed rain and sleet
            #  7: '',  # mixed snow and sleet
            #  8: '',  # freezing drizzle
            #  9: '',  # drizzle
            # 10: '',  # freezing rain
            11: '🌧',  # showers
            12: '🌧',  # rain
            # 13: '',  # snow flurries
            # 14: '',  # light snow showers
            # 15: '',  # blowing snow
            16: '❄',  # snow
            # 17: '',  # hail
            # 18: '',  # sleet
            # 19: '',  # dust
            20: '🌫',  # foggy
            # 21: '',  # haze
            # 22: '',  # smoky
            # 23: '',  # blustery
            24: '🍃',  # windy
            # 25: '',  # cold
            26: '☁',  # cloudy
            27: '⛅',  # mostly cloudy (night)
            28: '⛅',  # mostly cloudy (day)
            29: '🌤',  # partly cloudy (night)
            30: '🌤',  # partly cloudy (day)
            31: '🌑',  # clear (night)
            32: '☼',  # sunny
            33: '🌑',  # fair (night)
            34: '☼',  # fair (day)
            # 35: '',  # mixed rain and hail
            # 36: '',  # hot
            37: '⛈',  # isolated thunderstorms
            38: '⛈',  # scattered thunderstorms
            # 39: '',  # scattered showers (day)
            40: '⛆',  # heavy rain
            # 41: '',  # scattered snow showers (day)
            # 42: '',  # heavy snow
            # 43: '',  # blizzard
            # 44: '',  # not available
            # 45: '',  # scattered showers (night)
            # 46: '',  # scattered snow showers (night)
            47: '⛈',  # scattered thundershowers
        }
        data['symbol'] = condition_mapping.get(
            data.get('current_observation_condition_code', None),
            data.get('current_observation_condition_text', None)
        )
        data['current_observation_condition_symbol'] = data['symbol']  # for compatibility only

    def _get_wind_direction(self):
        wd = self.data.get('current_observation_wind_direction', None)
        if wd is None:
            return None
        return base._WeatherResponseParser.degrees_to_direction(wd)

    def _get_sunrise_time(self):
        dt = self.data.get('current_observation_astronomy_sunrise', None)
        if dt is None:
            return None
        return time.strftime(self.timeformat, time.strptime(dt, '%I:%M %p'))

    def _get_sunset_time(self):
        dt = self.data.get('current_observation_astronomy_sunset', None)
        if dt is None:
            return None
        return time.strftime(self.timeformat, time.strptime(dt, '%I:%M %p'))

    def _get_dt(self):
        dt = self.data.get('current_observation_pubDate', None)
        if dt is None:
            return None
        return time.strftime(self.dateformat + self.timeformat, time.localtime(dt))


class YahooWeather(GenPollUrl):
    """A weather widget, data provided by the Yahoo! Weather API.

    Some format options:
        - location_city
        - location_region
        - location_woeid
        - location_country
        - location_lat
        - location_long
        - location_timezone_id

        - weather
        - weather_details
        - isotime
        - units_temperature
        - units_wind_speed
        - humidity
        - pressure
        - sunrise
        - sunset
        - temp
        - visibility
        - wind_speed
        - wind_deg
        - wind_direction

        - symbol

        - current_observation_wind_chill
        - current_observation_atmosphere_rising
        - current_observation_condition_code
        - forecasts_0_day
        - forecasts_0_date
        - forecasts_0_low
        - forecasts_0_high
        - forecasts_0_text
        - forecasts_0_code
        - forecasts_9_day
        - forecasts_9_date
        - forecasts_9_low
        - forecasts_9_high
        - forecasts_9_text
        - forecasts_9_code
    """
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        # One of (woeid, location, coordinates) must be set.
        (
            'woeid',
            None,
            """Where On Earth ID. Can be looked up on e.g.:
            https://www.findmecity.com
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
            '{location_city}: {condition_temp} °{units_temperature}',
            'Display format'
        ),
        ('metric', True, 'True to use metric/C, False to use imperial/F'),
        (
            'dateformat',
            '%Y-%m-%d ',
            """Format for dates, defaults to ISO.
            For details see: https://docs.python.org/3/library/time.html#time.strftime"""
        ),
        (
            'timeformat',
            '%H:%M',
            """Format for times, defaults to ISO.
            For details see: https://docs.python.org/3/library/time.html#time.strftime"""
        ),
        ('up', '^', 'symbol for rising atmospheric pressure'),
        ('down', 'v', 'symbol for falling atmospheric pressure'),
        ('steady', 's', 'symbol for steady atmospheric pressure'),
    ]

    def __init__(self, **config):
        GenPollUrl.__init__(self, **config)
        self.add_defaults(YahooWeather.defaults)
        self.headers.update(HEADER)

    @property
    def url(self):
        if not self.woeid and not self.location and not self.coordinates:
            return None

        params = {
            'format': 'json',
            'u': 'c' if self.metric else 'f'
        }

        if self.woeid:
            params['woeid'] = self.woeid
        elif self.location:
            params['location'] = self.location
        elif self.coordinates:
            params['lat'] = self.coordinates['latitude']
            params['lon'] = self.coordinates['longitude']

        oauth = {
            'oauth_consumer_key': CONSUMER_KEY,
            'oauth_nonce': uuid.uuid4().hex,
            'oauth_signature_method': 'PLAINTEXT',
            'oauth_timestamp': str(int(time.time())),
            'oauth_version': '1.0',
            'oauth_signature': CONSUMER_SECRET
        }
        params.update(oauth)

        return QUERY_URL + urlencode(params) + '%26'

    def parse(self, response):
        try:
            rp = _YahooWeatherResponseParser(response, self.dateformat, self.timeformat)
        except Exception as e:
            return 'Error {}'.format(e)

        data = rp.data
        data['units_temperature'] = 'C' if self.metric else 'F'
        data['units_wind_speed'] = 'Km/h' if self.metric else 'm/h'

        if data.get('current_observation_atmosphere_rising', None) == '0':
            data['current_observation_atmosphere_rising'] = self.steady
        elif data.get('current_observation_atmosphere_rising', None) == '1':
            data['current_observation_atmosphere_rising'] = self.up
        elif data.get('current_observation_atmosphere_rising', None) == '2':
            data['current_observation_atmosphere_rising'] = self.down

        return self.format.format(**data)
