#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .. import bar
import base
import locale
import urllib
import urllib2
import gobject
import threading

try:
    import json
except ImportError:
    import simplejson as json


class BitcoinTicker(base._TextBox):
    ''' A bitcoin ticker widget, data provided by the btc-e.com API. Defaults to
        displaying currency in whatever the current locale is.
    '''

    QUERY_URL = "https://btc-e.com/api/2/btc_%s/ticker"

    defaults = [
        ('currency', locale.localeconv()['int_curr_symbol'].strip(),
            'The currency the value of bitcoin is displayed in'),
        ('format', 'BTC Buy: {buy}, Sell: {sell}',
            'Display format, allows buy, sell, high, low, avg, '
            'vol, vol_cur, last, variables.'),
        ('update_interval', 600, 'Update interval in seconds')
    ]

    def __init__(self, **config):
        base._TextBox.__init__(self, 'N/A', width=bar.CALCULATED, **config)
        self.add_defaults(BitcoinTicker.defaults)

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        self.timeout_add(self.update_interval, self.updater)

    def button_press(self, x, y, button):
        self.update(self.fetch_data())

    def updater(self):
        def worker():
            data = self.fetch_data()
            gobject.idle_add(self.update, data)
        threading.Thread(target=worker).start()
        return True

    def fetch_data(self):
        res = urllib2.urlopen(self.QUERY_URL % self.currency.lower())
        formatted = {}
        for k, v in json.loads(res.read())[u'ticker'].iteritems():
            formatted[k.encode('ascii')] = locale.currency(v)
        return formatted

    def update(self, data):
        if data:
            self.text = self.format.format(**data)
        else:
            self.text = 'N/A'
        self.bar.draw()
        return False
