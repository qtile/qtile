import locale

from libqtile.confreader import ConfigError
from libqtile.log_utils import logger
from libqtile.widget.generic_poll_text import GenPollUrl

_DEFAULT_CURRENCY = str(locale.localeconv()["int_curr_symbol"])
_DEFAULT_SYMBOL = str(locale.localeconv()["currency_symbol"])


class CryptoTicker(GenPollUrl):
    """
    A cryptocurrency ticker widget, data provided by the coinbase.com or the binance.com
    API. Defaults to displaying currency in whatever the current locale is. Examples:

        # display the average price of bitcoin in local currency
        widget.CryptoTicker()

        # display it in Euros:
        widget.CryptoTicker(currency="EUR")

        # or a different cryptocurrency!
        widget.CryptoTicker(crypto="ETH")

        # change the currency symbol:
        widget.CryptoTicker(currency="EUR", symbol="€")

        # display from Binance API
        widget.CryptoTicker(api="binance", currency="USDT")

    Widget requirements: aiohttp_.

    .. _aiohttp: https://pypi.org/project/aiohttp/
    """

    QUERY_URL_DICT = {
        "coinbase": (
            "https://api.coinbase.com/v2/prices/{}-{}/spot",
            lambda x: float(x["data"]["amount"]),
        ),
        "binance": (
            "https://api.binance.com/api/v3/ticker/price?symbol={}{}",
            lambda x: float(x["price"]),
        ),
    }

    defaults = [
        (
            "currency",
            _DEFAULT_CURRENCY.strip(),
            "The baseline currency that the value of the crypto is displayed in.",
        ),
        ("symbol", _DEFAULT_SYMBOL, "The symbol for the baseline currency."),
        ("crypto", "BTC", "The cryptocurrency to display."),
        ("format", "{crypto}: {symbol}{amount:.2f}", "Display string formatting."),
        ("api", "coinbase", "API that provides the data."),
    ]

    def __init__(self, **config):
        GenPollUrl.__init__(self, **config)
        self.add_defaults(CryptoTicker.defaults)

        # set up USD as the currency if no locale is set
        if self.currency == "":
            self.currency = "USD"
        # set up $ as the symbol if no locale is set
        if self.symbol == "":
            self.symbol = "$"

    def _configure(self, qtile, bar):
        try:
            GenPollUrl._configure(self, qtile, bar)
            self.query_url = self.QUERY_URL_DICT[self.api][0]
        except KeyError:
            apis = sorted(self.QUERY_URL_DICT.keys())
            logger.error(
                "%s is not a valid API. Use one of the list: %s.",
                self.api,
                apis,
            )
            raise ConfigError("Unknown provider passed as 'api' to CryptoTicker")

    @property
    def url(self):
        return self.query_url.format(self.crypto, self.currency)

    def parse(self, body):
        variables = dict()
        variables["crypto"] = self.crypto
        variables["symbol"] = self.symbol
        variables["amount"] = self.QUERY_URL_DICT[self.api][1](body)

        return self.format.format(**variables)
