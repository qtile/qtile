# -*- coding: utf-8 -*-

import base
from .. import manager, bar

import os.path
import imaplib


def gmail_unread(username, password):
    """ Returns the number of unread mails of an account. """

    M = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    M.login(username, password)

    status, counts = M.status("Inbox", "(MESSAGES UNSEEN)")

    unread = int(counts[0].split()[4][:-1])

    M.logout()

    return unread


class Gmail(base._TextBox):
    """
    A simple widget showing the number of new mails of a gmail account.

    You should have enabled IMAP in gmail in order to work.
    """

    defaults = manager.Defaults(
        ("font", "Arial", "Font"),
        ("fontsize", None, "Maildir widget font size. Calculated if None."),
        ("padding", None, "Maildir widget padding. Calculated if None."),
        ("background", "000000", "Background colour"),
        ("foreground", "ffffff", "Foreground colour")
        )

    def __init__(self, credentials_path, label="Mail: ", timeout=300, **config):
        """
        Constructor.

        @param credentials_path: the path to the Maildir (e.g. "~/Mail").
        @param timeout: the refresh timeout in seconds.
        """
        base._TextBox.__init__(self, "", bar.CALCULATED, **config)
        self._credentials = self.get_credentials(
                                os.path.expanduser(credentials_path))
        self._timeout = timeout
        self.label = label
        self.text = self.label + str(self.total_unread())

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        self.timeout_add(self._timeout, self.update)

    def get_credentials(self, path):
        """ Return a list of (username, password) tuples for every account. """
        credentials = []
        try:
            with open(path) as f1:
                for line in f1:
                    u, p = line.split()
                    credentials.append((u, p))
        except IOError:
            pass
        return credentials

    def total_unread(self):
        """ Get the total number of unread mails. """
        total = 0
        for user, password in self._credentials:
            total += gmail_unread(user, password)

        return total

    def update(self):
        """
        Updates the widget using mailbox_state and format_text.

        @return: True, to keep the timeout active.
        """
        newText = self.label + str(self.total_unread())

        if newText != self.text:
            self.text = newText
            self.bar.draw()

        # Return True to keep the timeout active (see documentation of
        # gobject.timeout_add()).
        return True
