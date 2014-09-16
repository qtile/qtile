from . import base
import imaplib
import re
import logging


logger = logging.getLogger('qtile')


class GmailChecker(base.ThreadedPollText):
    """
        A simple gmail checker.
        settings = {
            'username': username,
            'password': password,
            'email_path': valide email path,
            'fmt': "format string fot textbox widget",
            #if status_only_unseen is True
            #example "my unseen[%s]",
            #if status_only_unseen is False
            #example "messages: %s, unseen: %s"
            status_only_unseen: True or False
        }
    """
    defaults = [
        ("update_interval", 30, "Update time in seconds."),
        ("username", None, "username"),
        ("password", None, "password"),
        ("email_path", "INBOX", "email_path"),
        ("fmt", "inbox[%s],unseen[%s]", "fmt"),
        ("status_only_unseen", False, "Only show unseen messages"),
    ]

    def __init__(self, settings=None, **config):
        if settings is not None:
            base.deprecated("parameter settings is deprecated")
            config.updateAll(settings)
        base._TextBox.__init__(self, **config)
        self.add_defaults(GmailChecker.defaults)

    def poll(self):
        self.gmail = imaplib.IMAP4_SSL('imap.gmail.com')
        self.gmail.login(self.username, self.password)
        answer, raw_data = self.gmail.status(self.email_path,
                                             '(MESSAGES UNSEEN)')
        if answer == "OK":
            messages = int(re.search('MESSAGES\s+(\d+)', str(raw_data[0])).group(1))
            unseen = int(re.search('UNSEEN\s+(\d+)', str(raw_data[0])).group(1))
            if(self.status_only_unseen):
                return self.fmt % unseen
            else:
                return self.fmt % (messages, unseen)
        else:
            logger.exception(
                'GmailChecker UNKNOWN error, answer: %s, raw_data: %s'
                % (str(answer), str(raw_data)))
            return "UNKNOWN ERROR"
