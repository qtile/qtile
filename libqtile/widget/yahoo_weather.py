#!/usr/bin/env python
# -*- coding: utf-8 -*-

from . import base
from xml.dom import minidom
import json


from six.moves.urllib.request import urlopen
from six.moves.urllib.parse import urlencode

QUERY_URL = 'http://query.yahooapis.com/v1/public/yql?'
WEATHER_URL = 'http://weather.yahooapis.com/forecastrss?'
WEATHER_NS = 'http://xml.weather.yahoo.com/ns/rss/1.0'


class YahooWeather(base.ThreadedPollText):
    ''' A weather widget, data provided by the Yahoo! Weather API

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
    '''

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

    def __init__(self, **config):
        base.ThreadedPollText.__init__(self, **config)
        self.add_defaults(YahooWeather.defaults)

    def fetch_woeid(self, location):
        url = QUERY_URL + urlencode({
            'q': 'select woeid from geo.places where text="%s"' % location,
            'format': 'json'
        })
        try:
            response = urlopen(url)
            data = json.loads(response.read())
            if data['query']['count'] > 1:
                return data['query']['results']['place'][0]['woeid']
            return data['query']['results']['place']['woeid']
        except Exception:
            # HTTPError? JSON Error? KeyError? Doesn't matter, return None
            return None

    def poll(self):
        if not self.woeid:
            if self.location:
                self.woeid = self.fetch_woeid(self.location)
            if not self.woeid:
                return None
        format = 'c' if self.metric else 'f'
        url = WEATHER_URL + urlencode({'w': self.woeid, 'u': format})

        try:
            response = urlopen(url).read()
            dom = minidom.parseString(response)
        except Exception:
            # Invalid response or couldn't parse XML.
            return None

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
