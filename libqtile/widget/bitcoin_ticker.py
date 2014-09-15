#!/usr/bin/env python
# -*- coding: utf-8 -*-

from . import base
import locale

try:
    from urllib.request import urlopen  # Python 3
except ImportError:
    from urllib2 import urlopen  # Python 2

try:
    import json
except ImportError:
    import simplejson as json


class BitcoinTicker(base.ThreadedPollText):
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
    ]

    def __init__(self, **config):
        base.ThreadedPollText.__init__(self, **config)
        self.add_defaults(BitcoinTicker.defaults)

    def poll(self):
        res = urlopen(self.QUERY_URL % self.currency.lower())
        formatted = {}
        res = json.loads(res.read().decode())
        if 'error' in res and res['error'] == "invalid pair":
            locale.setlocale(locale.LC_MONETARY, "en_US.UTF-8")
            self.currency = locale.localeconv()['int_curr_symbol'].strip()
            res = urlopen(self.QUERY_URL % self.currency.lower())
            res = json.loads(res.read())
        for k, v in res['ticker'].items():
            formatted[k] = locale.currency(v)
        return self.format.format(**formatted)
