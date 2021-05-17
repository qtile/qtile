# Copyright (c) 2020 Matt Colligan
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


import textwrap

import pytest

from libqtile.backend.x11.xcbq import Connection
from test.conftest import BareConfig


@pytest.mark.parametrize("manager", [BareConfig], indirect=True)
def test_popup_focus(manager):
    manager.test_xeyes()
    conn = Connection(manager.display)
    _, _, windows = conn.default_screen.root.query_tree()
    start_wins = len(windows)

    success, msg = manager.c.eval(textwrap.dedent("""
        from libqtile.popup import Popup
        popup = Popup(self,
            x=0,
            y=0,
            width=self.current_screen.width,
            height=self.current_screen.height,
        )
        popup.place()
        popup.unhide()
    """))
    assert success, msg

    _, _, windows = conn.default_screen.root.query_tree()
    end_wins = len(windows)
    conn.finalize()
    assert end_wins == start_wins + 1

    assert manager.c.group.info()['focus'] == 'xeyes'
    assert manager.c.group.info()['windows'] == ['xeyes']
    assert len(manager.c.windows()) == 1
