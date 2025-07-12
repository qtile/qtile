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
    Check,
    RenamerTransformer,
    _QtileMigrator,
    add_migration,
)


class RenameWidgetTransformer(RenamerTransformer):
    from_to = ("CurrentLayoutIcon", "CurrentLayout")

    @m.leave(m.Call(func=m.Attribute(attr=m.Name("CurrentLayoutIcon"))))
    def add_kwarg_mode(self, original_node, updated_node) -> cst.Call:
        """Adds 'mode' keyword argument to 'CurrentLayout'."""
        self.lint(
            original_node,
            "CurrentLayout should add 'mode' keyword argument to have "
            "the same functionality as previous CurrentLayoutIcon.",
        )
        draw_kwarg = (
            cst.Arg(
                keyword=cst.Name("mode"),
                value=cst.SimpleString('"icon"'),
                equal=EQUALS_NO_SPACE,
            ),
        )
        new_args = draw_kwarg + original_node.args
        return updated_node.with_changes(args=new_args)


class RenameCurrentLayoutIcon(_QtileMigrator):
    ID = "RenameCurrentLayoutIcon"

    SUMMARY = "Removed ``CurrentLayoutIcon`` widget."

    HELP = """
    The ``CurrentLayoutIcon`` widget's functionality has
    been merged with ``CurrentLayout``.

    Example:

    .. code:: python

      widgets=[
          widget.CurrentLayoutIcon(),
          ...
      ],

    Should be updated as follows:

    .. code:: python

      widgets=[
          widget.CurrentLayout(mode="icon"),
          ...
      ],

    """

    AFTER_VERSION = "0.32.0"

    TESTS = [
        Check(
            """
            from libqtile import widget

            widget.CurrentLayoutIcon(font="sans")
            widget.CurrentLayoutIcon()
            widget.CurrentLayout(font="sans")
            widget.CurrentLayout()
            """,
            """
            from libqtile import widget

            widget.CurrentLayout(mode="icon", font="sans")
            widget.CurrentLayout(mode="icon")
            widget.CurrentLayout(font="sans")
            widget.CurrentLayout()
            """,
        )
    ]

    visitor = RenameWidgetTransformer


add_migration(RenameCurrentLayoutIcon)
