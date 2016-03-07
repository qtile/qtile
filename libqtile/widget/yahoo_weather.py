# -*- coding:utf-8 -*-
# Copyright (c) 2011-2012 dmpayton
# Copyright (c) 2011 Kenji_Takahashi
# Copyright (c) 2011 Mounier Florian
# Copyright (c) 2012, 2014-2015 Tycho Andersen
# Copyright (c) 2013 David R. Andersen
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2014 Sean Vig
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

from xml.dom import minidom

from six.moves.urllib.parse import urlencode

from . import base
from .generic_poll_text import GenPollUrl

QUERY_URL = 'http://query.yahooapis.com/v1/public/yql?'
WEATHER_URL = 'http://weather.yahooapis.com/forecastrss?'
WEATHER_NS = 'http://xml.weather.yahoo.com/ns/rss/1.0'


class YahooWeather(GenPollUrl):
    """A weather widget, data provided by the Yahoo! Weather API.

    Format options:

        - astronomy_sunrise
        - astronomy_sunset
        - atmosphere_humidity
        - atmosphere_visibility
        - atmosphere_pressure
        - atmosphere_rising
        - condition_text
        - condition_code
        - condition_temp
        - condition_date
        - location_city
        - location_region
        - location_country
        - units_temperature
        - units_distance
        - units_pressure
        - units_speed
        - wind_chill
    """
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        # One of (location, woeid) must be set.
        (
            'location',
            None,
            'Location to fetch weather for. Ignored if woeid is set.'
        ),
        (
            'woeid',
            None,
            'Where On Earth ID. Auto-calculated if location is set.'
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

    json = False

    def __init__(self, **config):
        GenPollUrl.__init__(self, **config)
        self.add_defaults(YahooWeather.defaults)
        self._url = None

    def fetch_woeid(self, location):
        url = QUERY_URL + urlencode({
            'q': 'select woeid from geo.places where text="%s"' % location,
            'format': 'json'
        })
        data = self.fetch(url)
        if data['query']['count'] > 1:
            return data['query']['results']['place'][0]['woeid']
        return data['query']['results']['place']['woeid']

    @property
    def url(self):
        if self._url:
            return self._url

        if not self.woeid:
            if self.location:
                self.woeid = self.fetch_woeid(self.location)
            if not self.woeid:
                return None
        format = 'c' if self.metric else 'f'
        self._url = WEATHER_URL + urlencode({'w': self.woeid, 'u': format})
        return self._url

    def parse(self, body):
        dom = minidom.parseString(body)

        structure = (
            ('location', ('city', 'region', 'country')),
            ('units', ('temperature', 'distance', 'pressure', 'speed')),
            ('wind', ('chill', 'direction', 'speed')),
            ('atmosphere', ('humidity', 'visibility', 'pressure', 'rising')),
            ('astronomy', ('sunrise', 'sunset')),
            ('condition', ('text', 'code', 'temp', 'date'))
        )

        data = {}
        for tag, attrs in structure:
            element = dom.getElementsByTagNameNS(WEATHER_NS, tag)[0]
            for attr in attrs:
                data['%s_%s' % (tag, attr)] = element.getAttribute(attr)

        if data['atmosphere_rising'] == '0':
            data['atmosphere_rising'] = self.steady
        elif data['atmosphere_rising'] == '1':
            data['atmosphere_rising'] = self.up
        elif data['atmosphere_rising'] == '2':
            data['atmosphere_rising'] = self.down

        return self.format.format(**data)
