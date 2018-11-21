# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 zordsdavini
# Copyright (c) 2014 Alexandr Kriptonov
# Copyright (c) 2014 Tycho Andersen
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

from libqtile.log_utils import logger
from . import base
import imaplib
import re


class GmailChecker(base.ThreadedPollText):
    """A simple gmail checker"""
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("update_interval", 30, "Update time in seconds."),
        ("username", None, "username"),
        ("password", None, "password"),
        ("email_path", "INBOX", "email_path"),
        ("fmt", "inbox[%s],unseen[%s]", "fmt"),
        ("status_only_unseen", False, "Only show unseen messages"),
    ]

    def __init__(self, **config):
        base._TextBox.__init__(self, **config)
        self.add_defaults(GmailChecker.defaults)

    def poll(self):
        self.gmail = imaplib.IMAP4_SSL('imap.gmail.com')
        self.gmail.login(self.username, self.password)
        answer, raw_data = self.gmail.status(self.email_path,
                                             '(MESSAGES UNSEEN)')
        if answer == "OK":
            dec = raw_data[0].decode()
            messages = int(re.search(r'MESSAGES\s+(\d+)', dec).group(1))
            unseen = int(re.search(r'UNSEEN\s+(\d+)', dec).group(1))
            if(self.status_only_unseen):
                return self.fmt % unseen
            else:
                return self.fmt % (messages, unseen)
        else:
            logger.exception(
                'GmailChecker UNKNOWN error, answer: %s, raw_data: %s',
                answer, raw_data)
            return "UNKNOWN ERROR"
