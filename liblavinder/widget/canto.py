# -*- coding: utf-8 -*-
# Copyright (c) 2011 Kenji_Takahashi
# Copyright (c) 2011 Mounier Florian
# Copyright (c) 2012, 2014 Tycho Andersen
# Copyright (c) 2014-2015 Sean Vig
# Copyright (c) 2014 Adi Sieker
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from . import base
from subprocess import call


class Canto(base.ThreadedPollText):
    """Display RSS feeds updates using the canto console reader"""
    orientations = base.ORIENTATION_HORIZONTAL
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
