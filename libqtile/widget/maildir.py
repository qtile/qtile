# -*- coding: utf-8 -*-
# vim: set sw=4 et tw=80:

import base

import os.path
import mailbox


class Maildir(base.ThreadedPollText):
    """
    A simple widget showing the number of new mails in maildir mailboxes.
    """

    defaults = [
        ("maildirPath", "~/Mail", "path to the Maildir folder"),
        ("subFolders", [], 'The subfolders to scan (e.g. [{"path": "INBOX", '
            '"label": "Home mail"}, {"path": "spam", "label": "Home junk"}]'),
        ("separator", " ", "the string to put between the subfolder strings."),
    ]

    def __init__(self, maildirPath=None, subFolders=None, separator=" ", **config):
        base.ThreadedPollText.__init__(self, **config)
        self.add_defaults(Maildir.defaults)

        if maildirPath is not None:
            base.deprecated("maildirPath is deprecated")
            self.maildirPath = maildirPath
        if subFolders is not None:
            base.deprecated("subFolders is deprecated")
            self.subFolders = subFolders
        if separator != " ":
            base.deprecated("separator is deprecated")
            self.separator = separator

        # if it looks like a list of strings then we just convert them
        # and use the name as the label
        if isinstance(self.subFolders[0], basestring):
            self.subFolders = [
                {"path": folder, "label": folder}
                for folder in subFolders
            ]

    def poll(self):
        """
        Scans the mailbox for new messages.

        @return: A string representing the current mailbox state.
        """
        state = {}

        def to_maildir_fmt(paths):
            for path in iter(paths):
                yield path.rsplit(":")[0]

        for subFolder in self.subFolders:
            path = os.path.join(self.maildirPath, subFolder["path"])
            maildir = mailbox.Maildir(path)
            state[subFolder["label"]] = 0

            for file in to_maildir_fmt(os.listdir(os.path.join(path, "new"))):
                if file in maildir:
                    state[subFolder["label"]] += 1

        return self.format_text(state)

    def format_text(self, state):
        """
        Converts the state of the subfolders to a string.

        @param state: a dictionary as returned by mailbox_state.
        @return: a string representation of the given state.
        """
        return self.separator.join(
            "{}: {}".format(*item) for item in state.iteritems()
        )
