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


class YahooWeather(GenPollUrl):
    """A weather widget, data provided by the Yahoo! Weather API.

    Format options:
        - location_city
        - location_region
        - location_woeid
        - location_country
        - location_lat
        - location_long
        - location_timezone_id
        - current_observation_wind_chill
        - current_observation_wind_direction
        - current_observation_wind_speed
        - current_observation_atmosphere_humidity
        - current_observation_atmosphere_visibility
        - current_observation_atmosphere_pressure
        - current_observation_atmosphere_rising
        - current_observation_astronomy_sunrise
        - current_observation_astronomy_sunset
        - current_observation_condition_text
        - current_observation_condition_symbol
        - current_observation_condition_code
        - current_observation_condition_temperature
        - current_observation_pubDate
        - forecasts_0_day
        - forecasts_0_date
        - forecasts_0_low
        - forecasts_0_high
        - forecasts_0_text
        - forecasts_0_code
        - forecasts_1_day
        - forecasts_1_date
        - forecasts_1_low
        - forecasts_1_high
        - forecasts_1_text
        - forecasts_1_code
        - forecasts_2_day
        - forecasts_2_date
        - forecasts_2_low
        - forecasts_2_high
        - forecasts_2_text
        - forecasts_2_code
        - forecasts_3_day
        - forecasts_3_date
        - forecasts_3_low
        - forecasts_3_high
        - forecasts_3_text
        - forecasts_3_code
        - forecasts_4_day
        - forecasts_4_date
        - forecasts_4_low
        - forecasts_4_high
        - forecasts_4_text
        - forecasts_4_code
        - forecasts_5_day
        - forecasts_5_date
        - forecasts_5_low
        - forecasts_5_high
        - forecasts_5_text
        - forecasts_5_code
        - forecasts_6_day
        - forecasts_6_date
        - forecasts_6_low
        - forecasts_6_high
        - forecasts_6_text
        - forecasts_6_code
        - forecasts_7_day
        - forecasts_7_date
        - forecasts_7_low
        - forecasts_7_high
        - forecasts_7_text
        - forecasts_7_code
        - forecasts_8_day
        - forecasts_8_date
        - forecasts_8_low
        - forecasts_8_high
        - forecasts_8_text
        - forecasts_8_code
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
            'Where On Earth ID. Precedence over location and coordinates.'
        ),
        (
            'location',
            None,
            'Location to fetch weather for. Precedence over coordinates.'
        ),
        (
            'coordinates',
            None,
            'Dictionary containing "latitude" and "longitude".'
        ),
        (
            'format',
            '{location_city}: {condition_temp} °{units_temperature}',
            'Display format'
        ),
        ('metric', True, 'True to use metric/C, False to use imperial/F'),
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

    def parse(self, body):
        data = self.flatten_json(body)
        data['units_temperature'] = 'C' if self.metric else 'F'

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
        data['current_observation_condition_symbol'] = condition_mapping.get(
            data['current_observation_condition_code'],
            data['current_observation_condition_text']
        )

        if data['current_observation_atmosphere_rising'] == '0':
            data['current_observation_atmosphere_rising'] = self.steady
        elif data['current_observation_atmosphere_rising'] == '1':
            data['current_observation_atmosphere_rising'] = self.up
        elif data['current_observation_atmosphere_rising'] == '2':
            data['current_observation_atmosphere_rising'] = self.down

        return self.format.format(**data)
