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

from libqtile.scripts.migrations._base import (
    Check,
    RenamerTransformer,
    _QtileMigrator,
    add_migration,
)


class RenameUnspecifiedTransformer(RenamerTransformer):
    from_to = ("UNSPECIFIED", "None")

    def strip_unspecified_imports(self, original_node, updated_node) -> cst.Import:
        new_names = list(filter(lambda n: n.name.value != "UNSPECIFIED", original_node.names))
        if len(new_names) == len(original_node.names):
            return original_node
        if len(new_names) == 0:
            return cst.RemoveFromParent()
        return updated_node.with_changes(names=new_names)

    def leave_Import(self, original_node: cst.Import, updated_node: cst.Import):  # noqa: N802
        return self.strip_unspecified_imports(original_node, updated_node)

    def leave_ImportFrom(  # noqa: N802
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ):
        return self.strip_unspecified_imports(original_node, updated_node)


class RenameUnspecified(_QtileMigrator):
    ID = "RenameUnspecified"

    SUMMARY = "Changes ``UNSPECIFIED`` argument to ``None``."

    HELP = """
    The UNSPECIFIED object was removed in favor of using python's None.
    """

    AFTER_VERSION = "0.24.0"

    TESTS = [
        Check(
            """
            from libqtile.widget.base import UNSPECIFIED, ORIENTATION_BOTH
            from libqtile.widget import TextBox
            from libqtile.layout import Tile

            tb = TextBox(text="hello")
            # just to use ORIENTATION_BOTH and force us to delete only the
            # right thing
            tb.orientations = ORIENTATION_BOTH
            tb.set_font(font=UNSPECIFIED)
            """,
            """
            from libqtile.widget.base import ORIENTATION_BOTH
            from libqtile.widget import TextBox
            from libqtile.layout import Tile

            tb = TextBox(text="hello")
            # just to use ORIENTATION_BOTH and force us to delete only the
            # right thing
            tb.orientations = ORIENTATION_BOTH
            tb.set_font(font=None)
            """,
        )
    ]

    visitor = RenameUnspecifiedTransformer


add_migration(RenameUnspecified)
