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
from libqtile.scripts.migrations._base import (
    Check,
    RenamerTransformer,
    _QtileMigrator,
    add_migration,
)


class RenameCheckUpdatesTransformer(RenamerTransformer):
    from_to = ("Pacman", "CheckUpdates")


class RenamePacmanWidget(_QtileMigrator):
    ID = "RenamePacmanWidget"

    SUMMARY = "Changes deprecated ``Pacman`` widget name to ``CheckUpdates``."

    HELP = """
    The ``Pacman`` widget has been renamed to ``CheckUpdates``.

    This is because the widget supports multiple package managers.

    Example:

    .. code:: python

      screens = [
          Screen(
              top=Bar(
                  [
                    ...
                    widget.Pacman(),
                    ...
                  ]
              )
          )
      ]

    Should be updated as follows:

    .. code:: python

      screens = [
          Screen(
              top=Bar(
                  [
                    ...
                    widget.CheckUpdates(),
                    ...
                  ]
              )
          )
      ]

    """

    AFTER_VERSION = "0.16.1"

    TESTS = [
        Check(
            """
            from libqtile import bar, widget
            from libqtile.widget import Pacman

            bar.Bar([Pacman(), widget.Pacman()], 30)
            """,
            """
            from libqtile import bar, widget
            from libqtile.widget import CheckUpdates

            bar.Bar([CheckUpdates(), widget.CheckUpdates()], 30)
            """,
        )
    ]

    visitor = RenameCheckUpdatesTransformer


add_migration(RenamePacmanWidget)
