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


class UpdateTogroupTransformer(MigrationTransformer):
    @m.call_if_inside(
        m.Call(func=m.Name(m.MatchIfTrue(lambda n: "togroup" in n)))
        | m.Call(func=m.Attribute(attr=m.Name(m.MatchIfTrue(lambda n: "togroup" in n))))
    )
    @m.leave(m.Arg(keyword=m.Name("groupName")))
    def update_togroup_args(self, original_node, updated_node) -> cst.Arg:
        """Changes 'groupName' kwarg to 'group_name'."""
        self.lint(
            original_node, "The 'groupName' keyword argument should be replaced with 'group_name."
        )
        return updated_node.with_changes(keyword=cst.Name("group_name"))


class UpdateTogroupArgs(_QtileMigrator):
    ID = "UpdateTogroupArgs"

    SUMMARY = "Updates ``groupName`` keyword argument to ``group_name``."

    HELP = """
    To be consistent with codestyle, the ``groupName`` argument in the ``togroup`` command needs to be
    changed to ``group_name``.


    The following code:

    .. code:: python

        lazy.window.togroup(groupName="1")

    will result in a warning in your logfile: ``Window.togroup's groupName is deprecated; use group_name``.

    The code should be updated to:

    .. code:: python

        lazy.window.togroup(group_name="1")

    """

    AFTER_VERSION = "0.18.1"

    TESTS = [
        Check(
            """
            from libqtile.config import Key
            from libqtile.lazy import lazy

            k = Key([], 's', lazy.window.togroup(groupName="g"))
            c = lambda win: win.togroup(groupName="g")
            """,
            """
            from libqtile.config import Key
            from libqtile.lazy import lazy

            k = Key([], 's', lazy.window.togroup(group_name="g"))
            c = lambda win: win.togroup(group_name="g")
            """,
        )
    ]

    visitor = UpdateTogroupTransformer


add_migration(UpdateTogroupArgs)
