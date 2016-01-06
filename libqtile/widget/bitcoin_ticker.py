# vim: tabstop=4 shiftwidth=4 expandtab
# Copyright (c) 2013 Jendrik Poloczek
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2014 Aborilov Pavel
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014-2015 Tycho Andersen
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
#
# -*- coding: utf-8 -*-

from . import base
from .generic_poll_text import GenPollUrl
import locale


class BitcoinTicker(GenPollUrl):
    '''
        A bitcoin ticker widget, data provided by the btc-e.com API. Defaults
        to displaying currency in whatever the current locale is.
    '''

    QUERY_URL = "https://btc-e.com/api/2/btc_%s/ticker"

    orientations = base.ORIENTATION_HORIZONTAL

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
