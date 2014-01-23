# -*- coding: utf-8 -*-
#
###################################################################

from .. import bar, utils
import base
import imaplib
import gobject
import threading
import re
import gnomekeyring as gk

class ImapWidget(base._TextBox):
    """
    This widget will scan one of your imap email boxes and report
    the number of unseen messages present.  I've configured it to
    only work with imap with ssl. Your password is obtained from
    the Gnome Keyring.  You can write your password to the keyring
    using the add-keyring-passwords.py script from my rxcomm-scripts
    repo at https://github.com/rxcomm/rxcomm-scripts.git

    Parameters for writing the password using the above script are:
        application name = imapwidget
        server = <fqdn of your imap server>
        user = <your userid>
        protocol = imapwidget
        password = <your password>

    mbox names must include the path to the mbox (except for the
    default INBOX).  So, for example if your mailroot is ~/Maildir,
    and you want to look at the mailbox at HomeMail/fred, the mbox
    setting would be: mbox='~/Maildir/HomeMail/fred'.  Labels
    can be whatever you choose, of course.
    """

    defaults = [
        ('mbox', 'INBOX', 'mailbox to fetch'),
        ('label', 'INBOX', 'label for display'),
        ('update_interval', 600, 'update interval'),
        ('user', None, 'email username'),
        ('server', None, 'email server name'),
    ]

    def __init__(self, **config):
        base._TextBox.__init__(self, 'IMAP not initialized',
                               width=bar.CALCULATED, **config)
        self.timeout_add(self.update_interval, self.imap_updater)

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        self.add_defaults(ImapWidget.defaults)
        self.layout = self.drawer.textlayout(
            self.text, self.foreground, self.font,
            self.fontsize, self.fontshadow, markup=True)

    def button_press(self, x, y, button):
        self.imap_updater()

    def imap_updater(self):
        self.log.info('adding IMAP widget timer')
        def worker():
            gobject.idle_add(self.fetch_imap)
        threading.Thread(target=worker).start()
        return True

    def fetch_imap(self):
        im = imaplib.IMAP4_SSL(self.server, 993)
        creds = self.get_pass(user=self.user, server=self.server, protocol='imapwidget')
        if creds[0] == 'Gnome Keyring Error':
            self.text = 'Gnome Keyring Error'
        else:
            im.login(self.user, creds)
            self.text = str(im.status(self.mbox, '(UNSEEN)')[1])
            self.text = self.label+': '+re.sub(r'\).*$', '', re.sub(r'^.*N\s', '', self.text))
            im.logout()
        self.bar.draw()

        return False

    def get_pass(self, **kwargs):

        try:
            keys = gk.find_network_password_sync(**kwargs)
            password = keys[0]['password']
            return password
        except (gk.NoMatchError, gk.IOError):
            self.log.critical('Gnome Keyring Error')
            return ('Gnome Keyring Error',)
