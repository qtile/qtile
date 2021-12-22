# Copyright (c) 2021 elParaguayo
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

# This widget is based on GenPollUrl which has a separate.
# We just need to test parsing here.

from libqtile import widget

RESPONSE = {"data": {"base": "BTC", "currency": "GBP", "amount": "29625.02"}}


def test_set_defaults():
    crypto = widget.CryptoTicker(currency="", symbol="")
    assert crypto.currency == "USD"
    assert crypto.symbol == "$"


def test_parse():
    crypto = widget.CryptoTicker(currency="GBP", symbol="£", crypto="BTC")
    assert crypto.url == "https://api.coinbase.com/v2/prices/BTC-GBP/spot"
    assert crypto.parse(RESPONSE) == "BTC: £29625.02"
