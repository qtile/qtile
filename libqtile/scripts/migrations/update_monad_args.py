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


class UpdateMonadLayoutTransformer(MigrationTransformer):
    @m.call_if_inside(
        m.Call(func=m.Name(m.MatchIfTrue(lambda n: n.startswith("Monad"))))
        | m.Call(func=m.Attribute(attr=m.Name(m.MatchIfTrue(lambda n: n.startswith("Monad")))))
    )
    @m.leave(m.Arg(keyword=m.Name("new_at_current")))
    def update_monad_args(self, original_node, updated_node) -> cst.Arg:
        """
        Changes 'new_at_current' kwarg to 'new_client_position' and sets correct
        value ('before|after_current').
        """
        self.lint(
            original_node, "The 'new_at_current' keyword argument in 'Monad' layouts is invalid."
        )
        new_value = cst.SimpleString(
            '"before_current"' if original_node.value.value == "True" else '"after_current"'
        )
        return updated_node.with_changes(keyword=cst.Name("new_client_position"), value=new_value)


class UpdateMonadArgs(_QtileMigrator):
    ID = "UpdateMonadArgs"

    SUMMARY = "Updates ``new_at_current`` keyword argument in Monad layouts."

    HELP = """
    Replaces the ``new_at_current=True|False`` argument in ``Monad*`` layouts with
    ``new_client_position`` to be consistent with other layouts.

    ``new_at_current=True`` is replaced with ``new_client_position="before_current`` and
    ``new_at_current=False`` is replaced with ``new_client_position="after_current"``.

    """

    AFTER_VERSION = "0.17.0"

    TESTS = [
        Check(
            """
            from libqtile import layout

            layouts = [
                layout.MonadTall(border_focus="#ff0000", new_at_current=False),
                layout.MonadWide(new_at_current=True, border_focus="#ff0000"),
            ]
            """,
            """
            from libqtile import layout

            layouts = [
                layout.MonadTall(border_focus="#ff0000", new_client_position="after_current"),
                layout.MonadWide(new_client_position="before_current", border_focus="#ff0000"),
            ]
            """,
        )
    ]

    visitor = UpdateMonadLayoutTransformer


add_migration(UpdateMonadArgs)
