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


class KeychordTransformer(MigrationTransformer):
    @m.leave(
        m.Call(
            func=m.Name("KeyChord"),
            args=[m.ZeroOrMore(), m.Arg(keyword=m.Name("mode")), m.ZeroOrMore()],
        )
    )
    def update_keychord_args(self, original_node, updated_node) -> cst.Call:
        """Changes 'mode' kwarg to 'mode' and 'value' kwargs."""
        args = original_node.args

        # (shouldn't be possible) if there are no args, stop here
        if not args:
            return original_node

        pos = 0

        # Look for the "mode" kwarg and get its position and value
        for i, arg in enumerate(args):
            if kwarg := arg.keyword:
                if kwarg.value == "mode":
                    # Ignore "mode" if it's already True or False
                    if m.matches(arg.value, (m.Name("True") | m.Name("False"))):
                        return original_node
                    pos = i
                    break
        # "mode" wasn't set so we can stop here
        else:
            return original_node

        self.lint(
            arg,  # We can pass the argument here which ensures the position is reported correctly
            "The use of mode='mode name' for KeyChord is deprecated. Use mode=True and value='mode name'.",
        )

        # Create two new kwargs
        # LibCST nodes are immutable so calling "with_changes" returns a new node
        name_arg = arg.with_changes(keyword=cst.Name("name"))
        mode_arg = arg.with_changes(value=cst.Name("True"))

        # Get the existing args and remove "mode"
        new_args = [a for i, a in enumerate(args) if i != pos]

        # Add "mode" and "value" kwargs
        new_args += [name_arg, mode_arg]

        # Return the updated node
        return updated_node.with_changes(args=new_args)


class KeychordArgs(_QtileMigrator):
    ID = "UpdateKeychordArgs"

    SUMMARY = "Updates ``KeyChord`` argument signature."

    HELP = """
    Previously, users could make a key chord persist by setting the `mode` to a string representing
    the name of the mode. For example:

    .. code:: python

        keys = [
            KeyChord(
                [mod],
                "x",
                [
                    Key([], "Up", lazy.layout.grow()),
                    Key([], "Down", lazy.layout.shrink())
                ],
                mode="Resize layout",
            )
        ]

    This will now result in the following warning message in the log file:

    .. code::

        The use of `mode` to set the KeyChord name is deprecated. Please use `name='Resize Layout'` instead.
        'mode' should be a boolean value to set whether the chord is persistent (True) or not."

    To remove the error, the config should be amended as follows:

    .. code:: python

        keys = [
            KeyChord(
                [mod],
                "x",
                [
                    Key([], "Up", lazy.layout.grow()),
                    Key([], "Down", lazy.layout.shrink())
                ],
                name="Resize layout",
            mode=True,
            )
        ]

    .. note::

       The formatting of the inserted argument may not correctly match your own formatting. You may this
       to run a tool like ``black`` after applying this migration to tidy up your code.

    """

    AFTER_VERSION = "0.21.0"

    TESTS = [
        Check(
            """
            from libqtile.config import Key, KeyChord
            from libqtile.lazy import lazy

            mod = "mod4"

            keys = [
                KeyChord(
                    [mod],
                    "x",
                    [
                        Key([], "Up", lazy.layout.grow()),
                        Key([], "Down", lazy.layout.shrink())
                    ],
                    mode="Resize layout",
                )
            ]
            """,
            """
            from libqtile.config import Key, KeyChord
            from libqtile.lazy import lazy

            mod = "mod4"

            keys = [
                KeyChord(
                    [mod],
                    "x",
                    [
                        Key([], "Up", lazy.layout.grow()),
                        Key([], "Down", lazy.layout.shrink())
                    ],
                    name="Resize layout",
                mode=True,
                )
            ]
            """,
        )
    ]

    visitor = KeychordTransformer


add_migration(KeychordArgs)
