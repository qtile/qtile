#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .. import bar
import base
import urllib
import urllib2
from xml.dom import minidom
import gobject
import threading

try:
    import json
except ImportError:
    import simplejson as json

QUERY_URL = 'http://query.yahooapis.com/v1/public/yql?'
WEATHER_URL = 'http://weather.yahooapis.com/forecastrss?'
WEATHER_NS = 'http://xml.weather.yahoo.com/ns/rss/1.0'


class YahooWeather(base._TextBox):
    ''' A weather widget, data provided by the Yahoo! Weather API
        Format options:
            astronomy_sunrise, astronomy_sunset
            atmosphere_humidity, atmosphere_visibility,
            atmosphere_pressure, atmosphere_rising
            condition_text, condition_code, condition_temp, condition_date
            location_city. location_region, location_country
            units_temperature, units_distance, units_pressure, units_speed
            wind_chill, wind_direction, wind_speed
    '''

    defaults = [
        ## One of (location, woeid) must be set.
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
        ('update_interval', 600, 'Update interval in seconds'),
        ('up', '^', 'symbol for rising atmospheric pressure'),
        ('down', 'v', 'symbol for falling atmospheric pressure'),
        ('steady', 's', 'symbol for steady atmospheric pressure'),
    ]

    def __init__(self, **config):
        base._TextBox.__init__(self, 'N/A', width=bar.CALCULATED, **config)

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        self.add_defaults(YahooWeather.defaults)
        self.timeout_add(self.update_interval, self.wx_updater)

    def button_press(self, x, y, button):
        self.update(self.fetch_weather())

    def wx_updater(self):
        self.log.info('adding WX widget timer')

        def worker():
            data = self.fetch_weather()
            gobject.idle_add(self.update, data)
        threading.Thread(target=worker).start()
        return True

    def update(self, data):
        if data:
            self.text = self.format.format(**data)
        else:
            self.text = 'N/A'
        self.bar.draw()
        return False

    def fetch_woeid(self, location):
        url = QUERY_URL + urllib.urlencode({
            'q': 'select woeid from geo.places where text="%s"' % location,
            'format': 'json'
        })
        try:
            response = urllib2.urlopen(url)
            data = json.loads(response.read())
            if data['query']['count'] > 1:
                return data['query']['results']['place'][0]['woeid']
            return data['query']['results']['place']['woeid']
        except Exception:
            ## HTTPError? JSON Error? KeyError? Doesn't matter, return None
            return None

    def fetch_weather(self):
        if not self.woeid:
            if self.location:
                self.woeid = self.fetch_woeid(self.location)
            if not self.woeid:
                return None
        format = 'c' if self.metric else 'f'
        url = WEATHER_URL + urllib.urlencode({'w': self.woeid, 'u': format})

        try:
            response = urllib2.urlopen(url).read()
            dom = minidom.parseString(response)
        except Exception:
            ## Invalid response or couldn't parse XML.
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

        return data
