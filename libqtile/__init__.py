from __future__ import absolute_import

import six

moves = [
    six.MovedAttribute("getoutput", "commands", "subprocess"),
]

for m in moves:
    six.add_move(m)

try:
    import asyncio
except ImportError:
    import trollius as asyncio

six.moves.asyncio = asyncio
