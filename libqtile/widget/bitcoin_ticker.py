from libqtile.widget.crypto_ticker import CryptoTicker
import logging

logger = logging.getLogger('BitcoinTicker')


class BitcoinTicker(CryptoTicker):
    """deprecated, in favor of CryptoTicker"""

    def __init__(self, **config):
        super().__init__(**config)
        logger.warning('BitcoinTicker widget is deprecated in favor of '
                       'CryptoTicker widget and will be removed in the future')
