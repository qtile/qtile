# -*- coding: utf-8 -*-
# Copyright (c) 2016 Tycho Andersen
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
from .generic_poll_text import GenPollUrl

import datetime


class IdleRPG(GenPollUrl):
    """
    A widget for monitoring and displaying IdleRPG stats.

    ::

        # display idlerpg stats for the player 'pants' on freenode's #idlerpg
        widget.IdleRPG(url="http://xethron.lolhosting.net/xml.php?player=pants")
    """

    orientations = base.ORIENTATION_HORIZONTAL

    defaults = [
        ('format', 'IdleRPG: {online} TTL: {ttl}', 'Display format'),
        ('json', False, 'Not json :)'),
        ('xml', True, 'Is XML :)'),
    ]

    def __init__(self, **config):
        GenPollUrl.__init__(self, **config)
        self.add_defaults(IdleRPG.defaults)

    def parse(self, body):
        formatted = {}
        for k, v in body['player'].items():
            if k == 'ttl':
                formatted[k] = str(datetime.timedelta(seconds=int(v)))
            elif k == 'online':
                formatted[k] = "online" if v == "1" else "offline"
            else:
                formatted[k] = v

        return self.format.format(**formatted)
