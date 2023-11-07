# Copyright (c) 2023 elParaguayo
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
import xcffib.xinput
import xcffib.xproto
import xcffib.xtest

from test.conftest import dualmonitor


@dualmonitor
def test_pointer(xmanager):
    """Two screens should result in 1 pointer barrier."""
    _, barriers = xmanager.c.eval("len(self.core.conn.xfixes.barriers.keys())")
    assert int(barriers) == 1


def test_no_pointer(xmanager):
    """One screen should result in 0 pointer barriers."""
    _, barriers = xmanager.c.eval("len(self.core.conn.xfixes.barriers.keys())")
    assert int(barriers) == 0


@dualmonitor
def test_screen_focus(xmanager, conn):
    def current_screen():
        _, index = xmanager.c.eval("self.current_screen.index")
        return int(index)

    assert current_screen() == 0

    _, barriers = xmanager.c.eval("len(self.core.conn.xfixes.barriers.keys())")

    xtest = conn.conn(xcffib.xtest.key)
    # Move to edge of barrier
    xtest.FakeInput(
        6, 0, xcffib.xproto.Time.CurrentTime, conn.default_screen.root.wid, 799, 100, 0
    )
    # Try to cross barrier
    xtest.FakeInput(6, 1, xcffib.xproto.Time.CurrentTime, conn.default_screen.root.wid, 1, 0, 0)
    conn.conn.flush()
    conn.xsync()

    # Second screen should now be focused
    assert current_screen() == 1

    # For some reason, FakeInput hits barrier in opposite direction but no barrierhit event is fired :(
    # So we can't include that part of the test here.
