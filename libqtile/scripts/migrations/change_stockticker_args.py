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
    Change,
    Check,
    MigrationTransformer,
    NoChange,
    _QtileMigrator,
    add_migration,
)


class StocktickerArgsTransformer(MigrationTransformer):
    @m.call_if_inside(
        m.Call(func=m.Name("StockTicker")) | m.Call(func=m.Attribute(attr=m.Name("StockTicker")))
    )
    @m.leave(m.Arg(keyword=m.Name("function")))
    def update_stockticker_args(self, original_node, updated_node) -> cst.Arg:
        """Changes 'function' kwarg to 'mode' and 'func' kwargs."""
        self.lint(original_node, "The 'function' keyword argument should be renamed 'func'.")
        return updated_node.with_changes(keyword=cst.Name("func"))


class StocktickerArgs(_QtileMigrator):
    ID = "UpdateStocktickerArgs"

    SUMMARY = "Updates ``StockTicker`` argument signature."

    HELP = """
    The ``StockTicker`` widget had a keyword argument called ``function``. This needs to be
    renamed to ``func`` to prevent clashes with the ``function()`` method of ``CommandObject``.

    For example:

    .. code:: python

        widget.StockTicker(function="TIME_SERIES_INTRADAY")

    should be changed to:

    .. code::

        widget.StockTicker(func="TIME_SERIES_INTRADAY")

    """

    AFTER_VERSION = "0.22.1"

    TESTS = [
        Change(
            """StockTicker(function="TIME_SERIES_INTRADAY")""",
            """StockTicker(func="TIME_SERIES_INTRADAY")""",
        ),
        Change(
            """widget.StockTicker(function="TIME_SERIES_INTRADAY")""",
            """widget.StockTicker(func="TIME_SERIES_INTRADAY")""",
        ),
        Change(
            """libqtile.widget.StockTicker(function="TIME_SERIES_INTRADAY")""",
            """libqtile.widget.StockTicker(func="TIME_SERIES_INTRADAY")""",
        ),
        NoChange("""StockTicker(func="TIME_SERIES_INTRADAY")"""),
        NoChange("""widget.StockTicker(func="TIME_SERIES_INTRADAY")"""),
        NoChange("""libqtile.widget.StockTicker(func="TIME_SERIES_INTRADAY")"""),
        Check(
            """
            import libqtile
            from libqtile import bar, widget
            from libqtile.widget import StockTicker

            bar.Bar(
                [
                    StockTicker(function="TIME_SERIES_INTRADAY"),
                    widget.StockTicker(function="TIME_SERIES_INTRADAY"),
                    libqtile.widget.StockTicker(function="TIME_SERIES_INTRADAY")
                ],
                20
            )
            """,
            """
            import libqtile
            from libqtile import bar, widget
            from libqtile.widget import StockTicker

            bar.Bar(
                [
                    StockTicker(func="TIME_SERIES_INTRADAY"),
                    widget.StockTicker(func="TIME_SERIES_INTRADAY"),
                    libqtile.widget.StockTicker(func="TIME_SERIES_INTRADAY")
                ],
                20
            )
            """,
        ),
    ]

    visitor = StocktickerArgsTransformer


add_migration(StocktickerArgs)
