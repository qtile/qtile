import json
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
        ('user_agent', 'Mozilla/5.0 (X11; Linux i686; rv:36.0) '
         'Gecko/20100101 Firefox/36.0', 'Set the user agent'),
        ('headers', {}, 'Extra Headers')
    ]

    def __init__(self, **config):
        base.ThreadedPollText.__init__(self, **config)
        self.add_defaults(GenPollUrl.defaults)

    def poll(self):
        if not self.parse or not self.url:
            return "Invalid config"

        data = self.data
        headers = {"User-agent": self.user_agent}
        if self.json:
            headers['Content-Type'] = 'application/json'

        if data and not isinstance(data, str):
            data = json.dumps(data)

        headers.update(self.headers)
        req = Request(self.url, data, headers)
        res = urlopen(req)
        body = res.read()
        if self.json:
            body = json.loads(body)

        try:
            text = self.parse(body)
        except Exception:
            text = "Can't parse"

        return text
