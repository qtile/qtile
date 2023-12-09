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


class RenameThreadedPollTextTransformer(RenamerTransformer):
    from_to = ("ThreadedPollText", "ThreadPoolText")


class RenameThreadedPollText(_QtileMigrator):
    ID = "RenameThreadedPollText"

    SUMMARY = "Replaces ``ThreadedPollText`` with ``ThreadPoolText``."

    HELP = """
    The ``ThreadedPollText`` class needs to replced with ``ThreadPoolText``.

    This is because the ``ThreadPoolText`` class can do everything that the
    ``ThreadedPollText`` does so the redundant code was removed.

    Example:

    .. code:: python

        from libqtile import widget

        class MyPollingWidget(widget.base.ThreadedPollText):
            ...

    Should be updated as follows:

    .. code:: python

        from libqtile import widget

        class MyPollingWidget(widget.base.ThreadPoolText):
            ...

    """

    AFTER_VERSION = "0.16.1"

    TESTS = [
        Check(
            """
            from libqtile.widget.base import ThreadedPollText

            class MyWidget(ThreadedPollText):
                pass
            """,
            """
            from libqtile.widget.base import ThreadPoolText

            class MyWidget(ThreadPoolText):
                pass
            """,
        )
    ]

    visitor = RenameThreadedPollTextTransformer


add_migration(RenameThreadedPollText)
