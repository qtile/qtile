from itertools import filterfalse

import libcst as cst
import libcst.matchers as m

from libqtile.scripts.migrations._base import (
    Check,
    MigrationTransformer,
    _QtileMigrator,
    add_migration,
)


class RenameUnspecifiedTransformer(MigrationTransformer):
    @m.leave(m.Call(func=m.Attribute(attr=m.Name("set_font"))))
    def update_unspecified_arg(self, original_node, updated_node) -> cst.Call:
        args = original_node.args

        def is_interesting_arg(arg):
            return m.matches(arg.value, m.Name("UNSPECIFIED"))

        args = list(filterfalse(is_interesting_arg, original_node.args))

        if len(args) == len(original_node.args):
            return original_node

        return updated_node.with_changes(args=args)

    def strip_unspecified_imports(self, original_node, updated_node) -> cst.Import:
        new_names = list(filter(lambda n: n.name.value != "UNSPECIFIED", original_node.names))
        if len(new_names) == len(original_node.names):
            return original_node
        self.lint(original_node, "'UNSPECIFIED' can be dropped")
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

    SUMMARY = "Drops `UNSPECIFIED` argument"

    HELP = """
    The UNSPECIFIED object was removed in favor of using the zero values (or
    None) to leave behavior unspecified. That is:

        font=UNSPECIFIED -> font=None
        fontsize=UNSPECIFIED -> fontsize=0
        fontshadow=UNSPECIFIED -> fontshadow=""
    """

    AFTER_VERSION = "0.25.0"

    TESTS = [
        Check(
            """
            from libqtile.widget.base import UNSPECIFIED, ORIENTATION_BOTH
            from libqtile.widget import TextBox
            from libqtile.layout import Tile

            tb = TextBox(text="hello")
            # just to use ORIENTATION_BOTH and force us to delete only the
            # right thing
            if False:
                tb.orientations = ORIENTATION_BOTH
                tb.set_font(font=UNSPECIFIED, fontsize=12)
            """,
            """
            from libqtile.widget.base import ORIENTATION_BOTH
            from libqtile.widget import TextBox
            from libqtile.layout import Tile

            tb = TextBox(text="hello")
            # just to use ORIENTATION_BOTH and force us to delete only the
            # right thing
            if False:
                tb.orientations = ORIENTATION_BOTH
                tb.set_font(fontsize=12)
            """,
        )
    ]

    visitor = RenameUnspecifiedTransformer


add_migration(RenameUnspecified)
