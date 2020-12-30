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


import pytest

from libqtile.backend.x11 import xcbq
from libqtile.popup import Popup
from test.conftest import BareConfig


@pytest.mark.parametrize("manager", [BareConfig], indirect=True)
def test_popup_focus(manager):
    manager.test_xeyes()
    manager.windows_map = {}

    # we have to add .conn so that Popup thinks this is libqtile.qtile
    manager.conn = xcbq.Connection(manager.display)

    try:
        popup = Popup(manager)
        popup.width = manager.c.screen.info()["width"]
        popup.height = manager.c.screen.info()["height"]
        popup.place()
        popup.unhide()
        assert manager.c.group.info()['focus'] == 'xeyes'
        assert manager.c.group.info()['windows'] == ['xeyes']
        assert len(manager.c.windows()) == 1
        popup.hide()
    finally:
        popup.kill()
        manager.conn.finalize()
