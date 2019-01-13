import json

from urllib.request import urlopen, Request

from libqtile.widget import base
from libqtile.log_utils import logger

try:
    import xmltodict

    def xmlparse(body):
        return xmltodict.parse(body)
except ImportError:
    # TODO: we could implement a similar parser by hand, but i'm lazy, so let's
    # punt for now
    def xmlparse(body):
        raise Exception("no xmltodict library")

from typing import Any, List, Tuple


class GenPollText(base.ThreadedPollText):
    """A generic text widget that polls using poll function to get the text"""
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ('func', None, 'Poll Function'),
    ]

    def __init__(self, **config):
        base.ThreadedPollText.__init__(self, **config)
        self.add_defaults(GenPollText.defaults)

    def poll(self):
        if not self.func:
            return "You need a poll function"
        return self.func()


class GenPollUrl(base.ThreadedPollText):
    """A generic text widget that polls an url and parses it using parse function"""
    orientations = base.ORIENTATION_HORIZONTAL
    defaults: List[Tuple[str, Any, str]] = [
        ('url', None, 'Url'),
        ('data', None, 'Post Data'),
        ('parse', None, 'Parse Function'),
        ('json', True, 'Is Json?'),
        ('user_agent', 'Qtile', 'Set the user agent'),
        ('headers', {}, 'Extra Headers'),
        ('xml', False, 'Is XML?'),
    ]

    def __init__(self, **config):
        base.ThreadedPollText.__init__(self, **config)
        self.add_defaults(GenPollUrl.defaults)

    def fetch(self, url, data=None, headers=None, is_json=True, is_xml=False):
        if headers is None:
            headers = {}
        req = Request(url, data, headers)
        res = urlopen(req)
        charset = res.headers.get_content_charset()

        body = res.read()
        if charset:
            body = body.decode(charset)

        if is_json:
            body = json.loads(body)

        if is_xml:
            body = xmlparse(body)
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
        body = self.fetch(self.url, data, headers, self.json, self.xml)

        try:
            text = self.parse(body)
        except Exception:
            logger.exception('got exception polling widget')
            text = "Can't parse"

        return text
