import json

import six
from six.moves.urllib.request import urlopen, Request

from libqtile.widget import base


class GenPollText(base.ThreadedPollText):
    """A generic text widget that polls using poll function to get the text"""

    defaults = [
        ('poll', None, 'Poll Function'),
    ]

    def __init__(self, **config):
        base.ThreadedPollText.__init__(self, **config)
        self.add_defaults(GenPollText.defaults)

    def poll(self):
        if not self.poll:
            return "You need a poll function"
        return self.poll()


class GenPollUrl(base.ThreadedPollText):
    """A generic text widget that polls an url and parses it
    using parse function"""

    defaults = [
        ('url', None, 'Url'),
        ('data', None, 'Post Data'),
        ('parse', None, 'Parse Function'),
        ('json', True, 'Is Json?'),
        ('user_agent', 'Qtile', 'Set the user agent'),
        ('headers', {}, 'Extra Headers')
    ]

    def __init__(self, **config):
        base.ThreadedPollText.__init__(self, **config)
        self.add_defaults(GenPollUrl.defaults)

    def fetch(self, url, data=None, headers={}, is_json=True):
        req = Request(url, data, headers)
        res = urlopen(req)
        if six.PY3:
            charset = res.headers.get_content_charset()
        else:
            charset = res.headers.getparam('charset')

        body = res.read()
        if charset:
            body = body.decode(charset)

        if is_json:
            body = json.loads(body)
        return body

    def poll(self):
        if not self.parse or not self.url:
            return "Invalid config"

        data = self.data
        headers = {"User-agent": self.user_agent}
        if self.json:
            headers['Content-Type'] = 'application/json'

        if data and not isinstance(data, str):
            data = json.dumps(data).encode()

        headers.update(self.headers)
        body = self.fetch(self.url, data, headers, self.json)

        try:
            text = self.parse(body)
        except Exception:
            text = "Can't parse"

        return text
