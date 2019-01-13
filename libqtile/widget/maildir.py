# -*- coding: utf-8 -*-
# Copyright (c) 2011 Timo Schmiade
# Copyright (c) 2012 Phil Jackson
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 Tycho Andersen
# Copyright (c) 2016 Christoph Lassner
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

from . import base

import os.path
import mailbox


class Maildir(base.ThreadedPollText):
    """A simple widget showing the number of new mails in maildir mailboxes"""
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("maildirPath", "~/Mail", "path to the Maildir folder"),
        ("subFolders", [], 'The subfolders to scan (e.g. [{"path": "INBOX", '
            '"label": "Home mail"}, {"path": "spam", "label": "Home junk"}]'),
        ("separator", " ", "the string to put between the subfolder strings."),
    ]

    def __init__(self, **config):
        base.ThreadedPollText.__init__(self, **config)
        self.add_defaults(Maildir.defaults)

        # if it looks like a list of strings then we just convert them
        # and use the name as the label
        if isinstance(self.subFolders[0], str):
            self.subFolders = [
                {"path": folder, "label": folder}
                for folder in self.subFolders
            ]

    def poll(self):
        """Scans the mailbox for new messages

        Returns
        =======
        A string representing the current mailbox state
        """
        state = {}

        def to_maildir_fmt(paths):
            for path in iter(paths):
                yield path.rsplit(":")[0]

        for subFolder in self.subFolders:
            path = os.path.join(os.path.expanduser(self.maildirPath),
                                subFolder["path"])
            maildir = mailbox.Maildir(path)
            state[subFolder["label"]] = 0

            for file in to_maildir_fmt(os.listdir(os.path.join(path, "new"))):
                if file in maildir:
                    state[subFolder["label"]] += 1

        return self.format_text(state)

    def format_text(self, state):
        """Converts the state of the subfolders to a string

        Parameters
        ==========
        state:
            a dictionary as returned by mailbox_state

        Returns
        =======
        a string representation of the given state
        """
        return self.separator.join(
            "{0}: {1}".format(*item) for item in state.items()
        )
