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
    Check,
    MigrationTransformer,
    _QtileMigrator,
    add_migration,
)

try:
    import isort

    can_sort = True
except ImportError:
    can_sort = False


class MatchRegexTransformer(MigrationTransformer):
    def __init__(self, *args, **kwargs):
        self.needs_import = False
        MigrationTransformer.__init__(self, *args, **kwargs)

    @m.call_if_inside(
        m.Call(func=m.Name("Match")) | m.Call(func=m.Attribute(attr=m.Name("Match")))
    )
    @m.leave(m.Arg(value=m.List(), keyword=m.Name()))
    def update_match_args(self, original_node, updated_node) -> cst.Arg:
        """Changes positional  argumentto 'widgets' kwargs."""
        name = original_node.keyword.value
        if not (all(isinstance(e.value, cst.SimpleString) for e in original_node.value.elements)):
            self.lint(
                original_node,
                f"The {name} keyword uses a list but the migrate script can not fix this as "
                f"not all elements are strings.",
            )
            return updated_node

        joined_text = "|".join(e.value.value.strip("'\"") for e in original_node.value.elements)
        regex = cst.parse_expression(f"""re.compile(r"^({joined_text})$")""")
        self.lint(
            original_node,
            f"The use of a list for the {name} argument is deprecated. "
            f"Please replace with 're.compile(r\"^({joined_text})$\")'.",
        )
        self.needs_import = True
        return updated_node.with_changes(value=regex)


class MatchListRegex(_QtileMigrator):
    ID = "MatchListRegex"

    SUMMARY = "Updates Match objects using lists"

    HELP = """
    The use of lists in ``Match`` objects is deprecated and should be
    replaced with a regex.

    For example:

    .. code:: python

        Match(wm_class=["one", "two"])

    should be changed to:

    .. code::

        Match(wm_class=re.compile(r"^(one|two)$"))

    """

    AFTER_VERSION = "0.23.0"

    TESTS = [
        Check(
            """
            from libqtile.config import Match

            Match(wm_class=["one", "two"])
            """,
            """
            import re

            from libqtile.config import Match

            Match(wm_class=re.compile(r"^(one|two)$"))
            """,
        ),
    ]

    def run(self, original_node):
        # Run the base transformer first...
        # This fixes simple replacements
        transformer = MatchRegexTransformer()
        updated = original_node.visit(transformer)

        # Update details of linting
        self.update_lint(transformer)

        # Check if we replaced any lists and now need to add re import
        if transformer.needs_import:
            # Create a context to store details of changes
            context = codemod.CodemodContext()
            AddImportsVisitor.add_needed_import(context, "re")
            add_visitor = AddImportsVisitor(context)

            # Run the transformations
            updated = add_visitor.transform_module(updated)

            if can_sort:
                updated = cst.parse_module(isort.code(updated.code))
            else:
                print("Unable to sort import lines.")

        return original_node, updated


add_migration(MatchListRegex)
