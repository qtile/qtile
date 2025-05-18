# Copyright (c) 2025, trimclain. All rights reserved.
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


class WlanArgsTransformer(MigrationTransformer):
    @m.call_if_inside(m.Call(func=m.Name("Wlan")) | m.Call(func=m.Attribute(attr=m.Name("Wlan"))))
    @m.leave(m.Arg(keyword=m.Name("ethernet_message")))
    def update_wlan_args(self, original_node, updated_node) -> cst.Arg:
        """Changes 'ethernet_message' to 'ethernet_message_format'."""
        self.lint(
            original_node,
            "The 'ethernet_message' argument is deprecated and should be replaced with 'ethernet_message_format'.",
        )
        return updated_node.with_changes(keyword=cst.Name("ethernet_message_format"))


class WlanArgs(_QtileMigrator):
    ID = "UpdateWlanArgs"

    SUMMARY = "Updates ``Wlan`` argument signature."

    HELP = """
    The ``Wlan`` widget previously accepted a ``ethernet_message`` keyword argument. This has
    been deprecated and should be replaced with a keyword argument named ``ethernet_message_format``.

    For example:

    .. code:: python

        widget.Wlan(ethernet_message="eth")

    should be changed to:

    .. code::

        widget.Wlan(ethernet_message_format="eth")

    """

    AFTER_VERSION = "0.31.0"

    TESTS = [
        Check(
            """
            from libqtile import bar, widget
            from libqtile.widget import Wlan

            bar.Bar(
                [
                    Wlan(ethernet_message="eth"),
                    widget.Wlan(ethernet_message="eth"),
                ],
                20,
            )
            """,
            """
            from libqtile import bar, widget
            from libqtile.widget import Wlan

            bar.Bar(
                [
                    Wlan(ethernet_message_format="eth"),
                    widget.Wlan(ethernet_message_format="eth"),
                ],
                20,
            )
            """,
        ),
    ]

    visitor = WlanArgsTransformer


add_migration(WlanArgs)
