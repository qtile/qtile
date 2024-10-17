# Copyright (c) 2021 elParaguayo
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

# Widget specific tests

from libqtile.widget import idlerpg

# Set up some fake responses
# Default widget displayes "ttl" and "online" values but can also show
# any others keys from the response so we need to include an extra field
online_response = {"player": {"ttl": 1000, "online": "1", "unused": "0"}}
offline_response = {"player": {"ttl": 10300, "online": "0"}}


# The GenPollURL widget has been tested separately so we just need to test parse
# method of this widget
def test_idlerpg():
    idler = idlerpg.IdleRPG()
    assert idler.parse(online_response) == "IdleRPG: online TTL: 0:16:40"
    assert idler.parse(offline_response) == "IdleRPG: offline TTL: 2:51:40"
