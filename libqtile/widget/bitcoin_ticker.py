#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .generic_poll_text import GenPollUrl
import locale


class BitcoinTicker(GenPollUrl):
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
        GenPollUrl.__init__(self, **config)
        self.add_defaults(BitcoinTicker.defaults)

    @property
    def url(self):
        return self.QUERY_URL % self.currency.lower()

    def parse(self, body):
        formatted = {}
        if 'error' in body and body['error'] == "invalid pair":
            locale.setlocale(locale.LC_MONETARY, "en_US.UTF-8")
            self.currency = locale.localeconv()['int_curr_symbol'].strip()
            body = self.fetch(self.url)
        for k, v in body['ticker'].items():
            formatted[k] = locale.currency(v)
        return self.format.format(**formatted)
