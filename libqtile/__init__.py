# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 Tycho Andersen
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

from __future__ import absolute_import

import six

moves = [
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
