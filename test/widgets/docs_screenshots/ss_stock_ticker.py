# Copyright (c) 2022 elParaguayo
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
import pytest

from libqtile.widget import stock_ticker

RESPONSE = {
    "Meta Data": {
        "1. Information": "Intraday (1min) open, high, low, close prices and volume",
        "2. Symbol": "QTIL",
        "3. Last Refreshed": "2021-07-30 19:09:00",
        "4. Interval": "1min",
        "5. Output Size": "Compact",
        "6. Time Zone": "US/Eastern",
    },
    "Time Series (1min)": {
        "2021-07-30 19:09:00": {
            "1. open": "140.9800",
            "2. high": "140.9800",
            "3. low": "140.9800",
            "4. close": "140.9800",
            "5. volume": "527",
        },
        "2021-07-30 17:27:00": {
            "1. open": "141.1900",
            "2. high": "141.1900",
            "3. low": "141.1900",
            "4. close": "141.1900",
            "5. volume": "300",
        },
        "2021-07-30 16:44:00": {
            "1. open": "141.0000",
            "2. high": "141.0000",
            "3. low": "141.0000",
            "4. close": "141.0000",
            "5. volume": "482",
        },
        "2021-07-30 16:26:00": {
            "1. open": "141.0000",
            "2. high": "141.0000",
            "3. low": "141.0000",
            "4. close": "141.0000",
            "5. volume": "102",
        },
    },
}


@pytest.fixture
def widget(monkeypatch):
    def result(self):
        return RESPONSE

    monkeypatch.setattr("libqtile.widget.stock_ticker.StockTicker.fetch", result)
    yield stock_ticker.StockTicker


@pytest.mark.parametrize("screenshot_manager", [{"symbol": "QTIL"}], indirect=True)
def ss_stock_ticker(screenshot_manager):
    screenshot_manager.take_screenshot()
