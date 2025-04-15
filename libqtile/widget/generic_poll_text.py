import json
import subprocess
from http.client import HTTPException
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from libqtile.log_utils import logger
from libqtile.widget import base

try:
    import xmltodict

    def xmlparse(body):
        return xmltodict.parse(body)

except ImportError:
    # TODO: we could implement a similar parser by hand, but i'm lazy, so let's
    # punt for now
    def xmlparse(body):
        raise Exception("no xmltodict library")


class GenPollText(base.ThreadPoolText):
    """A generic text widget that polls using poll function to get the text"""

    defaults = [
        ("func", None, "Poll Function"),
    ]

    def __init__(self, **config):
        base.ThreadPoolText.__init__(self, "", **config)
        self.add_defaults(GenPollText.defaults)

    def poll(self):
        if not self.func:
            return "You need a poll function"
        return self.func()


class GenPollUrl(base.ThreadPoolText):
    """A generic text widget that polls an url and parses it using parse function"""

    defaults: list[tuple[str, Any, str]] = [
        ("url", None, "Url"),
        ("data", None, "Post Data"),
        ("parse", None, "Parse Function"),
        ("json", True, "Is Json?"),
        ("user_agent", "Qtile", "Set the user agent"),
        ("headers", {}, "Extra Headers"),
        ("xml", False, "Is XML?"),
    ]

    def __init__(self, **config):
        base.ThreadPoolText.__init__(self, "", **config)
        self.add_defaults(GenPollUrl.defaults)

        self.headers["User-agent"] = self.user_agent
        if self.json:
            self.headers["Content-Type"] = "application/json"

        if self.data and not isinstance(self.data, str):
            self.data = json.dumps(self.data).encode()

    def fetch(self):
        req = Request(self.url, self.data, self.headers)
        res = urlopen(req)
        charset = res.headers.get_content_charset()

        body = res.read()
        if charset:
            body = body.decode(charset)

        if self.json:
            body = json.loads(body)

        if self.xml:
            body = xmlparse(body)
        return body

    def poll(self):
        if not self.parse or not self.url:
            return "Invalid config"

        try:
            body = self.fetch()
        except URLError:
            return "No network"
        except HTTPException:
            return "Request failed"

        try:
            text = self.parse(body)
        except Exception:
            logger.exception("got exception polling widget")
            text = "Can't parse"

        return text


class GenPollCommand(base.ThreadPoolText):
    """A generic text widget to display output from scripts or shell commands"""

    defaults = [
        ("update_interval", 60, "update time in seconds"),
        ("cmd", None, "command line as a string or list of arguments to execute"),
        ("shell", False, "run command through shell to enable piping and shell expansion"),
        ("parse", None, "Function to parse output of command"),
    ]

    def __init__(self, **config):
        base.ThreadPoolText.__init__(self, "", **config)
        self.add_defaults(GenPollCommand.defaults)

    def _configure(self, qtile, bar):
        base.ThreadPoolText._configure(self, qtile, bar)
        self.add_callbacks({"Button1": self.force_update})

    def poll(self):
        process = subprocess.run(
            self.cmd,
            capture_output=True,
            text=True,
            shell=self.shell,
        )
        if self.parse:
            return self.parse(process.stdout)

        return process.stdout.strip()
