# Copyright (c) 2017 Tycho Andersen
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

from six.moves.urllib.parse import urlencode
import locale

from .generic_poll_text import GenPollUrl


class StockTicker(GenPollUrl):
    """
    A stock ticker widget, based on the alphavantage API. Users must acquire an
    API key from https://www.alphavantage.co/support/#api-key

    The widget defaults to the TIME_SERIES_INTRADAY API function (i.e. stock
    symbols), but arbitrary Alpha Vantage API queries can be made by passing
    extra arguments to the constructor.

    ::

        # Display AMZN
        widget.StockTicker(apikey=..., symbol="AMZN")

        # Display BTC
        widget.StockTicker(apikey=..., function="DIGITAL_CURRENCY_INTRADAY", symbol="BTC", market="USD")
    """

    defaults = [
        ("interval", "1min", "The default latency to query"),
        ("function", "TIME_SERIES_INTRADAY", "The default API function to query"),
    ]

    def __init__(self, **config):
        GenPollUrl.__init__(self, **config)
        self.add_defaults(StockTicker.defaults)
        self.sign = locale.localeconv()['currency_symbol']
        self.query = {
            "interval": self.interval,
            "outputsize": "compact",
            "function": self.function
        }
        for k, v in config.items():
            self.query[k] = v

    @property
    def url(self):
        url = 'https://www.alphavantage.co/query?' + urlencode(self.query)
        return url

    def parse(self, body):
        last = None
        for k, v in body['Meta Data'].items():
            # In instead of ==, because of the number prefix that is inconsistent
            if "Last Refreshed" in k:
                last = v

        # Unfortunately, the actual data key is not consistently named, but
        # since there are only two and one is "Meta Data", we can just use the
        # other one.
        other = None
        for k, v in body.items():
            if k != "Meta Data":
                other = v
                break

        # The actual price is also not consistently named...
        price = None
        for k, v in other[last].items():
            if "price" in k or "close" in k:
                price = "{:0.2f}".format(float(v))
                break

        return "{symbol}: {sign}{price}".format(symbol=self.symbol, sign=self.sign, price=price)
