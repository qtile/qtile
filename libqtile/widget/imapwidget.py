import imaplib
import re

import keyring

from libqtile.confreader import ConfigError
from libqtile.log_utils import logger
from libqtile.widget import base


class ImapWidget(base.BackgroundPoll):
    """Email IMAP widget

    This widget will scan one of your imap email boxes and report the number of
    unseen messages present.  I've configured it to only work with imap with
    ssl. Your password can be obtained from the Gnome Keyring.

    Writing your password to the keyring initially is as simple as (changing
    out <userid> and <password> for your userid and password):

    1) create the file ~/.local/share/python_keyring/keyringrc.cfg with the
       following contents::

           [backend]
           default-keyring=keyring.backends.Gnome.Keyring
           keyring-path=/home/<userid>/.local/share/keyring/


    2) Execute the following python shell script once::

           #!/usr/bin/env python3
           import keyring
           user = <userid>
           password = <password>
           keyring.set_password('imapwidget', user, password)

    mbox names must include the path to the mbox (except for the default
    INBOX).  So, for example if your mailroot is ``~/Maildir``, and you want to
    look at the mailbox at HomeMail/fred, the mbox setting would be:
    ``mbox="~/Maildir/HomeMail/fred"``.  Note the nested sets of quotes! Labels
    can be whatever you choose, of course.

    If you want you can give password directly then Gnome Keyring will not be
    used.

    Widget requirements: keyring_.

    .. _keyring: https://pypi.org/project/keyring/
    """

    defaults = [
        ("mbox", '"INBOX"', "mailbox to fetch"),
        ("label", "INBOX: ", "label for display"),
        ("user", None, "email username"),
        ("password", None, "email password"),
        ("server", None, "email server name"),
        ("hide_no_unseen", False, "hide when there are no unseen messages"),
    ]

    def __init__(self, **config):
        base.BackgroundPoll.__init__(self, "", **config)
        self.add_defaults(ImapWidget.defaults)
        if self.user is None:
            raise ConfigError("You must set the 'user' parameter for the IMAP widget.")

        if self.password is None:
            password = keyring.get_password("imapwidget", self.user)
            if password is not None:
                self.password = password
            else:
                logger.critical("Gnome Keyring Error")

    def poll(self):
        im = imaplib.IMAP4_SSL(self.server, 993)
        if self.password is None:
            text = "No password error"
        else:
            im.login(self.user, self.password)
            status, response = im.status(self.mbox, "(UNSEEN)")
            im.logout()
            text = response[0].decode()
            count = re.sub(r"\).*$", "", re.sub(r"^.*N\s", "", text))
            if count == "0" and self.hide_no_unseen:
                return ""

            text = self.label + count
        return text
