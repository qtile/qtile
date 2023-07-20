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
    EQUALS_NO_SPACE,
    Change,
    Check,
    MigrationTransformer,
    NoChange,
    _QtileMigrator,
    add_migration,
)


class WidgetboxArgsTransformer(MigrationTransformer):
    @m.call_if_inside(
        m.Call(func=m.Name("WidgetBox")) | m.Call(func=m.Attribute(attr=m.Name("WidgetBox")))
    )
    @m.leave(m.Arg(keyword=None))
    def update_widgetbox_args(self, original_node, updated_node) -> cst.Arg:
        """Changes positional  argumentto 'widgets' kwargs."""
        self.lint(
            original_node,
            "The positional argument should be replaced with a keyword argument named 'widgets'.",
        )
        return updated_node.with_changes(keyword=cst.Name("widgets"), equal=EQUALS_NO_SPACE)


class WidgetboxArgs(_QtileMigrator):
    ID = "UpdateWidgetboxArgs"

    SUMMARY = "Updates ``WidgetBox`` argument signature."

    HELP = """
    The ``WidgetBox`` widget allowed a position argument to set the contents of the widget.
    This behaviour is deprecated and, instead, the contents should be specified with a
    keyword argument called ``widgets``.

    For example:

    .. code:: python

        widget.WidgetBox(
            [
                widget.Systray(),
                widget.Volume(),
            ]
        )

    should be changed to:

    .. code::

        widget.WidgetBox(
            widgets=[
                widget.Systray(),
                widget.Volume(),
            ]
        )

    """

    AFTER_VERSION = "0.20.0"

    TESTS = [
        Change(
            """
            widget.WidgetBox(
                [
                    widget.Systray(),
                    widget.Volume(),
                ]
            )
            """,
            """
            widget.WidgetBox(
                widgets=[
                    widget.Systray(),
                    widget.Volume(),
                ]
            )
            """,
        ),
        Change(
            """
            WidgetBox(
                [
                    widget.Systray(),
                    widget.Volume(),
                ]
            )
            """,
            """
            WidgetBox(
                widgets=[
                    widget.Systray(),
                    widget.Volume(),
                ]
            )
            """,
        ),
        NoChange(
            """
            widget.WidgetBox(
                widgets=[
                    widget.Systray(),
                    widget.Volume(),
                ]
            )
            """
        ),
        Check(
            """
            from libqtile import bar, widget
            from libqtile.widget import WidgetBox

            bar.Bar(
                [
                    WidgetBox(
                        [
                            widget.Systray(),
                            widget.Volume(),
                        ]
                    ),
                    widget.WidgetBox(
                        [
                            widget.Systray(),
                            widget.Volume(),
                        ]
                    )
                ],
                20,
            )
            """,
            """
            from libqtile import bar, widget
            from libqtile.widget import WidgetBox

            bar.Bar(
                [
                    WidgetBox(
                        widgets=[
                            widget.Systray(),
                            widget.Volume(),
                        ]
                    ),
                    widget.WidgetBox(
                        widgets=[
                            widget.Systray(),
                            widget.Volume(),
                        ]
                    )
                ],
                20,
            )
            """,
        ),
    ]

    visitor = WidgetboxArgsTransformer


add_migration(WidgetboxArgs)
