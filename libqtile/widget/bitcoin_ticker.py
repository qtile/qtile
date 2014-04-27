#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base
import locale
import urllib2

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
        res = urllib2.urlopen(self.QUERY_URL % self.currency.lower())
        formatted = {}
        for k, v in json.loads(res.read())[u'ticker'].iteritems():
            formatted[k.encode('ascii')] = locale.currency(v)
        return self.format.format(**formatted)
