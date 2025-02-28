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
    MigrationTransformer,
    _QtileMigrator,
    add_migration,
)


class BluetoothArgsTransformer(MigrationTransformer):
    @m.call_if_inside(
        m.Call(func=m.Name("Bluetooth")) | m.Call(func=m.Attribute(attr=m.Name("Bluetooth")))
    )
    @m.leave(m.Arg(keyword=m.Name("hci")))
    def update_bluetooth_args(self, original_node, updated_node) -> cst.Arg:
        """Changes positional  argumentto 'widgets' kwargs."""
        self.lint(
            original_node,
            "The 'hci' argument is deprecated and should be replaced with 'device'.",
        )
        return updated_node.with_changes(keyword=cst.Name("device"))


class BluetoothArgs(_QtileMigrator):
    ID = "UpdateBluetoothArgs"

    SUMMARY = "Updates ``Bluetooth`` argument signature."

    HELP = """
    The ``Bluetooth`` widget previously accepted a ``hci`` keyword argument. This has
    been deprecated following a major overhaul of the widget and should be replaced with
    a keyword argument named ``device``.

    For example:

    .. code:: python

        widget.Bluetooth(hci="/dev_XX_XX_XX_XX_XX_XX")

    should be changed to:

    .. code::

        widget.Bluetooth(device="/dev_XX_XX_XX_XX_XX_XX")

    """

    AFTER_VERSION = "0.23.0"

    TESTS = [
        Check(
            """
            from libqtile import bar, widget
            from libqtile.widget import Bluetooth

            bar.Bar(
                [
                    Bluetooth(hci="/dev_XX_XX_XX_XX_XX_XX"),
                    widget.Bluetooth(hci="/dev_XX_XX_XX_XX_XX_XX"),
                ],
                20,
            )
            """,
            """
            from libqtile import bar, widget
            from libqtile.widget import Bluetooth

            bar.Bar(
                [
                    Bluetooth(device="/dev_XX_XX_XX_XX_XX_XX"),
                    widget.Bluetooth(device="/dev_XX_XX_XX_XX_XX_XX"),
                ],
                20,
            )
            """,
        ),
    ]

    visitor = BluetoothArgsTransformer


add_migration(BluetoothArgs)
