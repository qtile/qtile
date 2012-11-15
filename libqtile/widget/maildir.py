# -*- coding: utf-8 -*-
# vim: set sw=4 et tw=80:

import base
from .. import manager, bar

import os.path
import mailbox

class Maildir(base._TextBox):
    """
    A simple widget showing the number of new mails in maildir mailboxes.
    """

    defaults = manager.Defaults(
        ("font", "Arial", "Font"),
        ("fontsize", None, "Maildir widget font size. Calculated if None."),
        ("padding", None, "Maildir widget padding. Calculated if None."),
        ("background", "000000", "Background colour"),
        ("foreground", "ffffff", "Foreground colour")
    )

    def __init__(self, maildirPath, subFolders,
                 separator=" ", timeout=120, **config):
        """
        Constructor.

        @param maildirPath: the path to the Maildir (e.g. "~/Mail").
        @param subFolders: the subfolders to scan (e.g. [{"path": "INBOX", "label": "Home mail"}, {"path": "spam", "label": "Home junk"}]).
        @param separator: the string to put between the subfolder strings.
        @param timeout: the refresh timeout in seconds.
        """
        base._TextBox.__init__(self, "", bar.CALCULATED, **config)
        self._maildirPath = os.path.expanduser(maildirPath)
        self._separator = separator
        self._timeout = timeout

        self._subFolders = []

        # if it looks like a list of strings then we just convert them
        # and use the name as the label
        if isinstance(subFolders[0], basestring):
            self._subFolders = [{"path": folder} for folder in subFolders]
        else:
            self._subFolders = subFolders

        self.text = self.format_text(self.mailbox_state())

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        self.timeout_add(self._timeout, self.update)

    def mailbox_state(self):
        """
        Scans the mailbox for new messages.

        @return: A dictionary mapping the entries from the subFolders parameter
                 passed to the constructor to the number of new mails in that
                 subfolder.
        """
        state = {}

        def to_maildir_fmt(paths):
            for path in iter(paths):
                yield path.rsplit(":")[0]

        for subFolder in self._subFolders:
            # if there's no label just use the path name
            subFolder.setdefault("label", subFolder["path"])

            path = os.path.join(self._maildirPath, subFolder["path"])
            maildir = mailbox.Maildir(path)
            state[subFolder["label"]] = 0

            for file in to_maildir_fmt(os.listdir(os.path.join(path, "new"))):
                if file in maildir:
                    state[subFolder["label"]] += 1

        return state

    def format_text(self, state):
        """
        Converts the state of the subfolders to a string.

        @param state: a dictionary as returned by mailbox_state.
        @return: a string representation of the given state.
        """
        return self._separator.join(
                "{}: {}".format(*item) for item in state.iteritems())

    def update(self):
        """
        Updates the widget using mailbox_state and format_text.

        @return: True, to keep the timeout active.
        """
        newText = self.format_text(self.mailbox_state())

        if newText != self.text:
            self.text = newText
            self.bar.draw()

        # Return True to keep the timeout active (see documentation of
        # gobject.timeout_add()).
        return True
