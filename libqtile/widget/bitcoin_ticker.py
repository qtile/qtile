#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .. import bar
import base
import urllib
import urllib2
import gobject
import threading

try:
    import json
except ImportError:
    import simplejson as json

class BitcoinTicker(base._TextBox):
    ''' A bitcoin ticker widget, data provided by the MtGox API
        Format options:
            buy, sell
    '''

    QUERY_URL = "http://data.mtgox.com/api/1/BTC%s/ticker_fast"
    currency_code = {'dollar' : 'USD', 'euro': 'EUR'}

    defaults = [
        ## One of (location, woeid) must be set.
        ('currency', 'dollar', 
         'The currency the value of bitcoin is displayed in'),
        ('format', 'BTC Buy: {buy}, Sell: {sell}', 'Display format'),
        ('update_interval', 600, 'Update interval in seconds')
    ]

    def __init__(self, **config):
        base._TextBox.__init__(self, 'N/A', width=bar.CALCULATED, **config)

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        self.add_defaults(BitcoinTicker.defaults)
        self.timeout_add(self.update_interval, self.wx_updater)

    def button_press(self, x, y, button):
        self.update(self.fetch_data())

    def wx_updater(self):
        self.log.info('adding WX widget timer')
        def worker():
            data = self.fetch_data()
            gobject.idle_add(self.update, data)
        threading.Thread(target=worker).start()
        return True

    def fetch_data(self):
        res = urllib2.urlopen(self.QUERY_URL % self.currency_code[self.currency])
        raw = json.loads(res.read())
        data = {'sell': raw['return']['sell']['display'], 
                'buy': raw['return']['buy']['display']}
        return data

    def update(self, data):
        if data:
            self.text = self.format.format(**data)
        else:
            self.text = 'N/A'
        self.bar.draw()
        return False
