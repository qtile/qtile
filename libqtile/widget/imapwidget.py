# -*- coding: utf-8 -*-
#
###################################################################

from . import base
import imaplib
import re
import keyring

class ImapWidget(base.ThreadedPollText):
    """
    This widget will scan one of your imap email boxes and report
    the number of unseen messages present.  I've configured it to
    only work with imap with ssl. Your password is obtained from
    the Gnome Keyring.

    Writing your password to the keyring initially is as simple as
    (changing out <userid> and <password> for your userid and password):

    1) create the file ~/.local/share/python_keyring/keyringrc.cfg
       with the following contents:

       [backend]
       default-keyring=keyring.backends.Gnome.Keyring
       keyring-path=/home/<userid>/.local/share/keyring/


    2) Execute the following python shell script once:

       #!/usr/bin/env python3
       import keyring
       user = <userid>
       password = <password>
       keyring.set_password('imapwidget', user, password)

    mbox names must include the path to the mbox (except for the
    default INBOX).  So, for example if your mailroot is ~/Maildir,
    and you want to look at the mailbox at HomeMail/fred, the mbox
    setting would be: mbox='"~/Maildir/HomeMail/fred"'.  Note the
    nested sets of quotes! Labels can be whatever you choose, of
    course.
    """

    defaults = [
        ('mbox', '"INBOX"', 'mailbox to fetch'),
        ('label', 'INBOX', 'label for display'),
        ('user', None, 'email username'),
        ('server', None, 'email server name'),
    ]

    def __init__(self, **config):
        base.ThreadedPollText.__init__(self, **config)
        self.add_defaults(ImapWidget.defaults)
        password = keyring.get_password('imapwidget', self.user)
        if password is not None:
            self.password = password
        else:
            self.log.critical('Gnome Keyring Error')
            return ('Gnome Keyring Error',)

    def poll(self):
        im = imaplib.IMAP4_SSL(self.server, 993)
        if self.password == 'Gnome Keyring Error':
            self.text = 'Gnome Keyring Error'
        else:
            im.login(self.user, self.password)
            status, response = im.status(self.mbox, '(UNSEEN)')
            self.text = response[0].decode()
            self.text = self.label + ': ' + re.sub(r'\).*$', '', re.sub(r'^.*N\s', '', self.text))
            im.logout()
        return self.text
