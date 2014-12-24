from __future__ import absolute_import

import six

moves = [
    six.MovedModule("gobject", "gobject", "gi.repository.GObject"),
    six.MovedAttribute("getoutput", "commands", "subprocess"),
]

for m in moves:
    six.add_move(m)

# Here, we can't use six.Moved* methods because being able to import asyncio vs
# trollius is not strictly Py 2 vs Py 3, but rather asyncio for >=3.4, and
# possibly 3.3 with Tulip, and trollius for 2 and <=3.2, and 3.3 without Tulip.
# Despite this, six.moves.asyncio makes a convenient place to store this so we
# don't need to keep try/except importing asyncio.
try:
    import asyncio
except ImportError:
    import trollius as asyncio

six.moves.asyncio = asyncio
