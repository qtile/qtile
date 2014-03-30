from .. import bar
import base
import imaplib
import re
import logging


_logger = logging.getLogger('qtile')


class GmailChecker(base._TextBox):
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
    ]

    def __init__(self, settings, width=bar.CALCULATED, **config):
        base._TextBox.__init__(self, "", width, **config)
        self.settings = settings
        self.add_defaults(GmailChecker.defaults)

    def validate_settings(self):
        self.not_validate = {}
        self.not_validate['status'] = False
        self.not_validate['messages'] = []
        _settings = self.settings
        _username = _settings.get('username', None)
        _password = _settings.get('password', None)
        _email_path = _settings.get('email_path', None)
        _fmt = _settings.get('fmt', None)
        _status_only_unseen = _settings.get('status_only_unseen', None)
        if(_username is None):
            self.not_validate['status'] = True
            _message = "not find username!"
            self.not_validate['messages'].append(_message)
        if(_password is None):
            self.not_validate['status'] = True
            _message = "not find password!"
            self.not_validate['messages'].append(_message)
        if(_email_path is None):
            self.settings['email_path'] = "INBOX"
        if(_fmt is None):
            self.settings['fmt'] = "inbox[%s],unseen[%s]"
            self.settings['status_only_unseen'] = False
        if(_status_only_unseen is None):
            self.settings['status_only_unseen'] = False

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        self.timeout_add(self.update_interval, self.update)

    def update(self):
        self.validate_settings()
        if(self.not_validate['status']):
            self.text = "BAD SETTINGS!"
            for _error in self.not_validate['messages']:
                _logger.exception('GmailChecker error: %s' % str(_error))
        else:
            self.gmail = imaplib.IMAP4_SSL('imap.gmail.com')
            try:
                self.gmail.login(self.settings['username'], self.settings['password'])
                answer, raw_data = \
                    self.gmail.status(
                        self.settings['email_path'],
                        '(MESSAGES UNSEEN)'
                    )
                if(answer == "OK"):
                    messages = int(re.search('MESSAGES\s+(\d+)', raw_data[0]).group(1))
                    unseen = int(re.search('UNSEEN\s+(\d+)', raw_data[0]).group(1))
                    if(self.settings['status_only_unseen']):
                        self.text = self.settings['fmt'] % unseen
                    else:
                        self.text = self.settings['fmt'] % (messages, unseen)
                else:
                    _logger.exception(
                        'GmailChecker UNKNOWN error, answer: %s, raw_data: %s'
                        % (str(answer), str(raw_data)))
                    self.text = "UNKNOWN ERROR"
            except Exception, _error:
                _logger.exception('GmailChecker error: %s' % str(_error))
                self.text = "ERROR"
        self.bar.draw()
        return True
