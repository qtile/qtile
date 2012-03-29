#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .. import hook, bar, manager
import base
import urllib
import urllib2
from xml.dom import minidom

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
            atmosphere_humidity, atmosphere_visibility, atmosphere_pressure, atmosphere_rising
            condition_text, condition_code, condition_temp, condition_date
            location_city. location_region, location_country
            units_temperature, units_distance, units_pressure, units_speed
            wind_chill, wind_direction, wind_speed
    '''

    defaults = manager.Defaults(
        ('font', 'Arial', 'Font'),
        ('fontsize', None, 'Pixel size, calculated if None.'),
        ('padding', None, 'Padding, calculated if None.'),
        ('background', '000000', 'Background colour'),
        ('foreground', 'ffffff', 'Foreground colour'),

        ## One of (location, woeid) must be set.
        ('location', None, 'Location to fetch weather for. Ignored if woeid is set.'),
        ('woeid', None, 'Where On Earth ID. Auto-calculated if location is set.'),
        ('format', '{location_city}: {condition_temp} °{units_temperature}', 'Display format'),
        ('metric', True, 'True to use metric/C, False to use imperial/F'),
        ('update_interval', 600, 'Update interval in seconds'),
    )
    def __init__(self, **config):
        base._TextBox.__init__(self, 'N/A', width=bar.CALCULATED, **config)

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        self.timeout_add(self.update_interval, self.update)

    def click(self, x, y, button):
        self.update()

    def update(self):
        if not self.woeid and self.location:
            self.woeid = self.fetch_woeid(self.location)
        if self.woeid:
            data = self.fetch_weather(self.woeid, self.metric)
            if data:
                self.text = self.format.format(**data)
            else:
                self.text = 'N/A'
        else:
            self.text = 'N/A'
        self.bar.draw()
        return True

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
        except Exception, err:
            ## HTTPError? JSON Error? KeyError? Doesn't matter, return None
            return None

    def fetch_weather(self, woeid, metric):
        format = 'c' if metric else 'f'
        url = WEATHER_URL + urllib.urlencode({'w': woeid, 'u': format})

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
        return data
