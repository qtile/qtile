# Copyright (c) 2025, Tycho Andersen. All rights reserved.
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


class MigrateThreadPoolTextTransformer(RenamerTransformer):
    from_to = ("ThreadPoolText", "BackgroundPoll")


class MigrateThreadPoolText(_QtileMigrator):
    ID = "MigrateThreadPoolText"

    SUMMARY = "Replaces ``ThreadPoolText`` with ``BackgroundPoll``."

    HELP = """
    The ``ThreadPoolText`` class is deprecated and should be replaced with
    ``BackgroundPoll``.
    """

    AFTER_VERSION = "0.33.0"

    TESTS = [
        Check(
            """
            from libqtile.widget.base import ThreadPoolText

            class MyWidget(ThreadPoolText):
                pass
            """,
            """
            from libqtile.widget.base import BackgroundPoll

            class MyWidget(BackgroundPoll):
                pass
            """,
        ),
        Check(
            """
            from libqtile.widget import base

            class MyWidget(base.ThreadPoolText):
                def __init__(self, **config):
                    base.ThreadPoolText.__init__(self, "", **config)

                def poll(self):
                    return "some text"
            """,
            """
            from libqtile.widget import base

            class MyWidget(base.BackgroundPoll):
                def __init__(self, **config):
                    base.BackgroundPoll.__init__(self, "", **config)

                def poll(self):
                    return "some text"
            """,
        ),
    ]

    visitor = MigrateThreadPoolTextTransformer


add_migration(MigrateThreadPoolText)
