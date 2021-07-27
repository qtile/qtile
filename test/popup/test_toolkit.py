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
import textwrap


def test_grid_layout(manager):
    success, msg = manager.c.eval(textwrap.dedent("""
        from libqtile.popup.toolkit import (
            PopupGridLayout,
            PopupText,
        )

        controls = [
            PopupText(text="Text1", row=0, col=0, col_span=2, row_span=2),
            PopupText(text="Text2", row=2, col=1)
        ]

        layout = PopupGridLayout(
            self,
            controls=controls,
            rows=4,
            cols=2,
            margin=0
        )

        layout.show(0, 0)
    """))
    assert success, msg

    layout = manager.c.internal_windows()[0]
    assert layout["name"] == "popupgridlayout"
    assert len(layout["controls"]) == 2

    # Check control positions
    text1 = layout["controls"][0]
    assert text1["x"] == 0
    assert text1["y"] == 0
    assert text1["width"] == 200  # 2 cols out of 2
    assert text1["height"] == 100  # 2 rows out of 4

    text2 = layout["controls"][1]
    assert text2["x"] == 100
    assert text2["y"] == 100
    assert text2["width"] == 100  # 1 cols out of 2
    assert text2["height"] == 50  # 1 rows out of 4


def test_relative_layout(manager):
    success, msg = manager.c.eval(textwrap.dedent("""
        from libqtile.popup.toolkit import (
            PopupRelativeLayout,
            PopupText,
        )

        controls = [
            PopupText(text="Text1", pos_x=0.1, pos_y=0.2, width=0.6, height=0.4),
            PopupText(text="Text2", pos_x=0.7, pos_y=0.6, width=0.2, height=0.3)
        ]

        layout = PopupRelativeLayout(
            self,
            controls=controls,
            margin=0
        )

        layout.show(0, 0)
    """))
    assert success, msg

    layout = manager.c.internal_windows()[0]
    assert layout["name"] == "popuprelativelayout"
    assert len(layout["controls"]) == 2

    # Check control positions
    text1 = layout["controls"][0]
    assert text1["x"] == 20
    assert text1["y"] == 40
    assert text1["width"] == 120
    assert text1["height"] == 80

    text2 = layout["controls"][1]
    assert text2["x"] == 140
    assert text2["y"] == 120
    assert text2["width"] == 40
    assert text2["height"] == 60


def test_absolute_layout(manager):
    success, msg = manager.c.eval(textwrap.dedent("""
        from libqtile.popup.toolkit import (
            PopupAbsoluteLayout,
            PopupText,
        )

        controls = [
            PopupText(text="Text1", pos_x=15, pos_y=15, width=180, height=40),
            PopupText(text="Text2", pos_x=15, pos_y=115, width=100, height=30)
        ]

        layout = PopupAbsoluteLayout(
            self,
            controls=controls,
            margin=0
        )

        layout.show(0, 0)
    """))
    assert success, msg

    layout = manager.c.internal_windows()[0]
    assert layout["name"] == "popupabsolutelayout"
    assert len(layout["controls"]) == 2

    # Check control positions
    text1 = layout["controls"][0]
    assert text1["x"] == 15
    assert text1["y"] == 15
    assert text1["width"] == 180
    assert text1["height"] == 40

    text2 = layout["controls"][1]
    assert text2["x"] == 15
    assert text2["y"] == 115
    assert text2["width"] == 100
    assert text2["height"] == 30
