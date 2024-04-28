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
from libcst.codemod.visitors import AddImportsVisitor, RemoveImportsVisitor

from libqtile.scripts.migrations._base import (
    Change,
    MigrationTransformer,
    _QtileMigrator,
    add_migration,
)

MODULE_MAP = {
    "window": cst.parse_expression("libqtile.backend.x11.window"),
}

IMPORT_MAP = {
    "window": ("libqtile.backend.x11", "window"),
}


class ModuleRenamesTransformer(MigrationTransformer):
    """
    This transfore does a number of things:
    - Where possible, it replaces module names directly. It is able to do so where
      the module is shown in its dotted form e.g. libqtile.command_graph.
    - In addition, it identifies where modules are imported from libqtile and
      stores these values in a list where they can be accessed later.
    """

    def __init__(self, *args, **kwargs):
        self.from_imports = []
        MigrationTransformer.__init__(self, *args, **kwargs)

    def do_lint(self, original_node, module):
        if module == "window":
            self.lint(
                original_node,
                "The 'libqtile.window' has been moved to 'libqtile.backend.x11.window'.",
            )

    @m.leave(
        m.ImportAlias(
            name=m.Attribute(
                value=m.Name("libqtile"), attr=m.Name(m.MatchIfTrue(lambda x: x in MODULE_MAP))
            )
        )
    )
    def update_import_module_names(self, original_node, updated_node) -> cst.ImportAlias:
        """Renames modules in 'import ...' statements."""
        module = original_node.name.attr.value
        self.do_lint(original_node, module)

        new_module = MODULE_MAP[module]
        return updated_node.with_changes(name=new_module)

    @m.leave(
        m.ImportFrom(
            module=m.Attribute(
                value=m.Name("libqtile"), attr=m.Name(m.MatchIfTrue(lambda x: x in MODULE_MAP))
            )
        )
    )
    def update_import_from_module_names(self, original_node, updated_node) -> cst.ImportFrom:
        """Renames modules in 'from ... import ...' statements."""
        module = original_node.module.attr.value
        self.do_lint(original_node, module)
        new_module = MODULE_MAP[module]
        return updated_node.with_changes(module=new_module)

    @m.leave(
        m.ImportFrom(
            module=m.Name("libqtile"),
            names=[
                m.ZeroOrMore(),
                m.ImportAlias(name=m.Name(m.MatchIfTrue(lambda x: x in IMPORT_MAP))),
                m.ZeroOrMore(),
            ],
        )
    )
    def tag_from_imports(self, original_node, _) -> cst.ImportFrom:
        """Marks which modules are"""
        for name in original_node.names:
            if name.name.value in IMPORT_MAP:
                self.lint(original_node, f"From libqtile import {name.name.value} is deprecated.")
                self.from_imports.append(name.name.value)

        return original_node


class ModuleRenames(_QtileMigrator):
    ID = "ModuleRenames"

    SUMMARY = "Updates certain deprecated ``libqtile.`` module names."

    HELP = """
    ``libqtile.window`` module was moved to ``libqtile.backend.x11.window``.
    """

    AFTER_VERSION = "0.18.1"

    TESTS = []

    for mod, (new_mod, new_file) in IMPORT_MAP.items():
        TESTS.append(Change(f"import libqtile.{mod}", f"import {new_mod}.{new_file}"))
        TESTS.append(
            Change(f"from libqtile.{mod} import foo", f"from {new_mod}.{new_file} import foo")
        )
        TESTS.append(Change(f"from libqtile import {mod}", f"from {new_mod} import {new_file}"))

    def run(self, original_node):
        # Run the base transformer first...
        # This fixes simple replacements
        transformer = ModuleRenamesTransformer()
        updated = original_node.visit(transformer)

        # Update details of linting
        self.update_lint(transformer)

        # Check if we found any 'from libqtile import ...` lines which
        # need to be updated
        if transformer.from_imports:
            # Create a context to store details of changes
            context = codemod.CodemodContext()

            for name in transformer.from_imports:
                # For each import, get base name and module name from the map
                base, module = IMPORT_MAP[name]

                # Remove the old 'from libqtile import name'
                RemoveImportsVisitor.remove_unused_import(context, "libqtile", name)

                # Add correct import line
                AddImportsVisitor.add_needed_import(context, base, module)

            # Create the visitors. The advantage of using these is that they will
            # handle the cases where there are multiple imports in the same line.
            remove_visitor = RemoveImportsVisitor(context)
            add_visitor = AddImportsVisitor(context)

            # Rune the transformations
            updated = remove_visitor.transform_module(updated)
            updated = add_visitor.transform_module(updated)

        return original_node, updated


add_migration(ModuleRenames)
