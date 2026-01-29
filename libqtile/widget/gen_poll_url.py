import json
from typing import Any

import aiohttp

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


class GenPollUrl(base.BackgroundPoll):
    """A generic text widget that polls an url and parses it using parse function


    Widget requirements: aiohttp_.

    .. _aiohttp: https://pypi.org/project/aiohttp/
    """

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
        base.BackgroundPoll.__init__(self, "", **config)
        self.add_defaults(GenPollUrl.defaults)

        self.headers["User-agent"] = self.user_agent
        if self.json:
            self.headers["Content-Type"] = "application/json"

        if self.data and not isinstance(self.data, str):
            self.data = json.dumps(self.data).encode()

    async def apoll(self):
        if not self.parse or not self.url:
            return "Invalid config"

        headers = self.headers.copy()
        data = self.data

        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method="POST" if data else "GET", url=self.url, data=data, headers=headers
                ) as response:
                    if self.json:
                        body = await response.json()
                    elif self.xml:
                        text_body = await response.text()
                        body = xmlparse(text_body)
                    else:
                        body = await response.text()

            text = self.parse(body)
        except Exception:
            logger.exception("got exception polling widget")
            text = "Can't parse"

        return text
