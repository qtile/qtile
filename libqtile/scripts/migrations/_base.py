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
from __future__ import annotations

import difflib
from textwrap import dedent
from typing import TYPE_CHECKING

import libcst
import libcst.matchers as m

from libqtile.scripts.migrations import MIGRATIONS

if TYPE_CHECKING:
    from typing import ClassVar, Collection, Type

    from libcst.metadata.base_provider import ProviderT


# By default, libcst adds spaces around "=" so we should remove them
EQUALS_NO_SPACE = libcst.AssignEqual(
    whitespace_before=libcst.SimpleWhitespace(
        value="",
    ),
    whitespace_after=libcst.SimpleWhitespace(
        value="",
    ),
)

RED = "\033[38;2;255;0;0m"
GREEN = "\033[38;2;0;255;0m"
END = "\033[38;2;255;255;255m"


def add_migration(migration):
    MIGRATIONS.append(migration)


def add_colours(lines):
    coloured = []
    for line in lines:
        if line.startswith("+"):
            coloured.append(f"{GREEN}{line}{END}")
        elif line.startswith("-"):
            coloured.append(f"{RED}{line}{END}")
        else:
            coloured.append(line)

    return coloured


class LintLine:
    def __init__(self, pos, message: str = "", migrator_id: str = "") -> None:
        self.line = pos.line
        self.col = pos.column
        self.message = message
        self.id = migrator_id
        self._pos = (pos.line, pos.column)

    def set_id(self, migration_id: str = "") -> LintLine:
        self.id = migration_id
        return self

    def __lt__(self, other: LintLine) -> bool:
        if not isinstance(other, LintLine):
            raise ValueError
        return self._pos < other._pos

    def __str__(self) -> str:
        return "[Ln {line}, Col {col}]: {message} ({id})".format(**self.__dict__)


class MigrationHelper:
    """
    Migrations may need to access details about the position of the match (e.g. for linting) and
    the parent node.

    These are accessible via metadata providers so this class sets the relevant dependencies
    and provides some helper functions.
    """

    METADATA_DEPENDENCIES: ClassVar[Collection["ProviderT"]] = (
        libcst.metadata.PositionProvider,
        libcst.metadata.ParentNodeProvider,
    )

    def __init__(self) -> None:
        self._lint_lines: list[LintLine] = []

    def lint(self, node, message) -> None:
        pos = self.get_metadata(libcst.metadata.PositionProvider, node).start  # type: ignore[attr-defined]
        self._lint_lines.append(LintLine(pos, message))

    def get_parent(self, node) -> libcst.CSTNode:
        return self.get_metadata(libcst.metadata.ParentNodeProvider, node)  # type: ignore[attr-defined]


class MigrationTransformer(MigrationHelper, m.MatcherDecoratableTransformer):
    def __init__(self, *args, **kwargs):
        m.MatcherDecoratableTransformer.__init__(self, *args, **kwargs)
        MigrationHelper.__init__(self)


class MigrationVisitor(MigrationHelper, m.MatcherDecoratableVisitor):
    def __init__(self, *args, **kwargs):
        m.MatcherDecoratableVisitor.__init__(self, *args, **kwargs)
        MigrationHelper.__init__(self)


class RenamerTransformer(MigrationTransformer):
    """
    Very basic transformer. Will replace every instance of 'old_name'
    with 'new_name'.

    To use: subclass RenameTransformer and set the class attribute
    'from_to' with ('old_name', 'new_name')
    """

    from_to = ("old_name", "new_name")

    def leave_Name(self, original_node, updated_node):  # noqa: N802
        if original_node.value == self.from_to[0]:
            self.lint(original_node, "'{0}' should be replaced with '{1}'.".format(*self.from_to))
            return updated_node.with_changes(value=self.from_to[1])
        return original_node


class Change:
    def __init__(self, input_code, output_code):
        self.input = input_code
        self.output = output_code
        self.check = False


class NoChange(Change):
    def __init__(self, input_code):
        Change.__init__(self, input_code, input_code)


class Check(Change):
    def __init__(self, input_code, output_code):
        Change.__init__(self, input_code, output_code)
        self.check = True


class _QtileMigrator:
    ID: str = "UniqueMigrationName"

    SUMMARY: str = "Brief summary of migration"

    HELP: str = """
    More detailed description of the migration including purpose and example changes.
    """

    AFTER_VERSION: str = ""

    TESTS: list[Change] = []

    # Set the name of the visitor/transformer here
    visitor: Type[MigrationVisitor] | Type[MigrationTransformer] | None = None

    def __init__(self) -> None:
        self._lint_lines: list[LintLine] = []
        self.original: libcst.metadata.MetadataWrapper | None = None
        self.updated: libcst.Module | None = None

    def update_lint(self, visitor) -> None:
        self._lint_lines += [line.set_id(self.ID) for line in visitor._lint_lines]

    def show_lint(self) -> list[LintLine]:
        """
        Return a list of LintLine objects storing details of deprecated code.
        """
        return self._lint_lines

    @classmethod
    def show_help(cls) -> str:
        return dedent(cls.HELP)

    @classmethod
    def show_summary(cls) -> str:
        return cls.SUMMARY

    @classmethod
    def show_id(cls) -> str:
        return cls.ID

    @classmethod
    def get_version(cls) -> tuple[int, ...]:
        return tuple(int(x) for x in cls.AFTER_VERSION.split("."))

    def show_diff(self, no_colour=False) -> str:
        """
        Return a string showing the generated diff.
        """
        if self.original is None or self.updated is None:
            return ""

        original = self.original.module
        updated = self.updated

        diff = difflib.unified_diff(
            original.code.splitlines(), updated.code.splitlines(), "original", "modified"
        )

        if not no_colour:
            diff = add_colours(list(diff))

        try:
            a, b, *lines = diff
            joined = "\n".join(lines)
            return f"{a}{b}{joined}"
        except ValueError:
            # No difference so we stop here.
            return ""

    def migrate(self, original) -> None:
        original, updated = self.run(original)
        self.original = original
        self.updated = updated

    def run(
        self, original
    ) -> tuple[libcst.Module | libcst.metadata.MetadataWrapper, libcst.Module]:
        """
        Run the migration set in 'visitor'.

        Method can be overriden for more complex scenarios (e.g. multiple transformers).
        """
        if self.visitor is None:
            raise AttributeError("Migration has not defined a 'visitor' attribute.")

        transformer = self.visitor()
        updated = original.visit(transformer)
        self.update_lint(transformer)

        return original, updated
