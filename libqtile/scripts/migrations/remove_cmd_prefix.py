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
from libcst import codemod
from libcst.codemod.visitors import AddImportsVisitor

from libqtile.scripts.migrations._base import (
    Change,
    Check,
    MigrationTransformer,
    NoChange,
    _QtileMigrator,
    add_migration,
)

# Three methods had their names changed beyond removing the prefix
MIGRATION_MAP = {
    "cmd_hints": "get_hints",
    "cmd_groups": "get_groups",
    "cmd_screens": "get_screens",
    "cmd_opacity": "set_opacity",
}


def is_cmd(value):
    return value.startswith("cmd_")


class CmdPrefixTransformer(MigrationTransformer):
    def __init__(self, *args, **kwargs):
        MigrationTransformer.__init__(self, *args, **kwargs)
        self.needs_import = False

    @m.call_if_inside(m.Call())
    @m.leave(m.Name(m.MatchIfTrue(is_cmd)))
    def change_func_call_name(self, original_node, updated_node) -> cst.Name:
        """Removes cmd_prefix from a call where the command begins with the cmd_ prefix."""
        name = original_node.value

        if name in MIGRATION_MAP:
            replacement = MIGRATION_MAP[name]

        else:
            replacement = name[4:]

        self.lint(
            original_node,
            f"Use of 'cmd_' prefix is deprecated. '{name}' should be replaced with '{replacement}'",
        )

        return updated_node.with_changes(value=replacement)

    @m.call_if_inside(m.ClassDef())
    @m.leave(m.FunctionDef(name=m.Name(m.MatchIfTrue(is_cmd))))
    def change_func_def(self, original_node, updated_node) -> cst.FunctionDef:
        """
        Renames method definitions using the cmd_ prefix and adds the
        @expose_command decorator.

        Also sets a flag to show that the script should add the relevant
        import if it's missing.
        """
        decorator = cst.Decorator(cst.Name("expose_command"))
        name = original_node.name
        updated = name.with_changes(value=name.value[4:])

        self.lint(
            original_node,
            "Use of 'cmd_' prefix is deprecated. Use '@expose_command' when defining methods.",
        )

        self.needs_import = True

        return updated_node.with_changes(name=updated, decorators=[decorator])


class RemoveCmdPrefix(_QtileMigrator):
    ID = "RemoveCmdPrefix"

    SUMMARY = "Removes ``cmd_`` prefix from method calls and definitions."

    HELP = """
    The ``cmd_`` prefix was used to identify methods that should be exposed to
    qtile's command API. This has been deprecated and so calls no longer require
    the prefix.

    For example:

    .. code:: python

      qtile.cmd_spawn("vlc")

    would be replaced with:

    .. code:: python

      qtile.spawn("vlc")

    Where users have created their own widgets with methods using this prefix,
    the syntax has also changed:

    For example:

    .. code:: python

        class MyWidget(libqtile.widget.base._Widget):
            def cmd_my_command(self):
                pass

    Should be updated as follows:

    .. code:: python

        from libqtile.command.base import expose_command

        class MyWidget(libqtile.widget.base._Widget):
            @expose_command
            def my_command(self):
                pass
    """

    AFTER_VERSION = "0.22.1"

    TESTS = [
        Change("""qtile.cmd_spawn("alacritty")""", """qtile.spawn("alacritty")"""),
        Change("""qtile.cmd_groups()""", """qtile.get_groups()"""),
        Change("""qtile.cmd_screens()""", """qtile.get_screens()"""),
        Change("""qtile.current_window.cmd_hints()""", """qtile.current_window.get_hints()"""),
        Change(
            """qtile.current_window.cmd_opacity(0.5)""",
            """qtile.current_window.set_opacity(0.5)""",
        ),
        Change(
            """
            class MyWidget(widget.Clock):
                def cmd_my_command(self):
                    pass
            """,
            """
            from libqtile.command.base import expose_command

            class MyWidget(widget.Clock):
                @expose_command
                def my_command(self):
                    pass
            """,
        ),
        NoChange(
            """
            def cmd_some_other_func():
                pass
            """
        ),
        Check(
            """
            from libqtile import qtile, widget

            class MyClock(widget.Clock):
                def cmd_my_exposed_command(self):
                    pass

            def my_func(qtile):
                qtile.cmd_spawn("rickroll")
                hints = qtile.current_window.cmd_hints()
                groups = qtile.cmd_groups()
                screens = qtile.cmd_screens()
                qtile.current_window.cmd_opacity(0.5)

            def cmd_some_other_func():
                pass
            """,
            """
            from libqtile import qtile, widget
            from libqtile.command.base import expose_command

            class MyClock(widget.Clock):
                @expose_command
                def my_exposed_command(self):
                    pass

            def my_func(qtile):
                qtile.spawn("rickroll")
                hints = qtile.current_window.get_hints()
                groups = qtile.get_groups()
                screens = qtile.get_screens()
                qtile.current_window.set_opacity(0.5)

            def cmd_some_other_func():
                pass
            """,
        ),
    ]

    def run(self, original):
        # Run the base migrations
        transformer = CmdPrefixTransformer()
        updated = original.visit(transformer)
        self.update_lint(transformer)

        # Check if we need to add an import line
        if transformer.needs_import:
            # We use the built-in visitor to add the import
            context = codemod.CodemodContext()
            AddImportsVisitor.add_needed_import(
                context, "libqtile.command.base", "expose_command"
            )
            visitor = AddImportsVisitor(context)

            # Run the visitor over the updated code
            updated = updated.visit(visitor)

        return original, updated


add_migration(RemoveCmdPrefix)
