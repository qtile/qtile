# -*- coding: utf-8 -*-

from . import base
from subprocess import call


class Canto(base.ThreadedPollText):
    """
        Display RSS feeds updates using the canto console reader.
    """
    defaults = [
        ("fetch", False, "Whether to fetch new items on update"),
        ("feeds", [], "List of feeds to display, empty for all"),
        ("one_format", "{name}: {number}", "One feed display format"),
        ("all_format", "{number}", "All feeds display format"),
    ]

    def __init__(self, **config):
        base.ThreadedPollText.__init__(self, **config)
        self.add_defaults(Canto.defaults)

    def poll(self):
        if not self.feeds:
            arg = "-a"
            if self.fetch:
                arg += "u"
            output = self.all_format.format(
                number=self.call_process(["canto", arg])[:-1]
            )
            return output
        else:
            if self.fetch:
                call(["canto", "-u"])
            return "".join([self.one_format.format(
                name=feed,
                number=self.call_process(["canto", "-n", feed])[:-1]
            ) for feed in self.feeds])
