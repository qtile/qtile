# Copyright (c) 2023, elParaguayo. All rights reserved.
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
import libcst as cst
import libcst.matchers as m

from libqtile.scripts.migrations._base import (
    Check,
    RenamerTransformer,
    _QtileMigrator,
    add_migration,
)


def is_bitcoin(func):
    name = func.value
    if hasattr(func, "attr"):
        attr = func.attr.value
    else:
        attr = None

    return name == "BitcoinTicker" or attr == "BitcoinTicker"


class BitcoinTransformer(RenamerTransformer):
    from_to = ("BitcoinTicker", "CryptoTicker")

    @m.leave(
        m.Call(
            func=m.MatchIfTrue(is_bitcoin),
            args=[m.ZeroOrMore(), m.Arg(keyword=m.Name("format")), m.ZeroOrMore()],
        )
    )
    def remove_format_kwarg(self, original_node, updated_node) -> cst.Call:
        """Removes the 'format' keyword argument from 'BitcoinTracker'."""
        new_args = [a for a in original_node.args if a.keyword.value != "format"]
        new_args[-1] = new_args[-1].with_changes(comma=cst.MaybeSentinel.DEFAULT)
        return updated_node.with_changes(args=new_args)


class BitcoinToCrypto(_QtileMigrator):
    ID = "UpdateBitcoin"

    SUMMARY = "Updates ``BitcoinTicker`` to ``CryptoTicker``."

    HELP = """
    The ``BitcoinTicker`` widget has been renamed ``CryptoTicker``. In addition, the ``format``
    keyword argument is removed during this migration as the available fields for the format
    have changed.

    The removal only happens on instances of ``BitcoinTracker``. i.e. running ``qtile migrate``
    on the following code:

    .. code:: python

        BitcoinTicker(format="...")
        CryptoTicker(format="...")

    will return:

    .. code:: python

        CryptoTicker()
        CryptoTicker(format="...")

    """

    AFTER_VERSION = "0.18.0"

    TESTS = [
        Check(
            """
            from libqtile import bar
            from libqtile.widget import BitcoinTicker

            bar.Bar(
                [
                    BitcoinTicker(crypto='BTC', format='BTC: {avg}'),
                    BitcoinTicker(format='{crypto}: {avg}', font='sans'),
                    BitcoinTicker(),
                    BitcoinTicker(currency='EUR', format='{avg}', foreground='ffffff'),
                ],
                30
            )
            """,
            """
            from libqtile import bar
            from libqtile.widget import CryptoTicker

            bar.Bar(
                [
                    CryptoTicker(crypto='BTC'),
                    CryptoTicker(font='sans'),
                    CryptoTicker(),
                    CryptoTicker(currency='EUR', foreground='ffffff'),
                ],
                30
            )
            """,
        )
    ]

    visitor = BitcoinTransformer


add_migration(BitcoinToCrypto)
