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


class RenameHookTransformer(RenamerTransformer):
    from_to = ("window_name_change", "client_name_updated")


class RenameWindowNameHook(_QtileMigrator):
    ID = "RenameWindowNameHook"

    SUMMARY = "Changes ``window_name_changed`` hook name."

    HELP = """
    The ``window_name_changed`` hook has been replaced with
    ``client_name_updated``.

    Example:

    .. code:: python

      @hook.subscribe.window_name_changed
      def my_func(window):
          ...

    Should be updated as follows:

    .. code:: python

      @hook.subscribe.client_name_updated
      def my_func(window):
          ...

    """

    AFTER_VERSION = "0.16.1"

    TESTS = [
        Check(
            """
            from libqtile import hook

            @hook.subscribe.window_name_change
            def f():
                pass
            """,
            """
            from libqtile import hook

            @hook.subscribe.client_name_updated
            def f():
                pass
            """,
        )
    ]

    visitor = RenameHookTransformer


add_migration(RenameWindowNameHook)
