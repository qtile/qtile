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


def test_popup_menu_from_dbus(manager):
    success, msg = manager.c.eval(textwrap.dedent("""
        from libqtile.popup.menu import PopupMenu
        from libqtile.widget.statusnotifier import DBusMenuItem

        items = [
            DBusMenuItem(
                None,
                id=0,
                item_type="",
                enabled=True,
                visible=True,
                label="Menu Item 1"
            ),
            DBusMenuItem(
                None,
                id=0,
                item_type="",
                enabled=True,
                visible=False,
                label="Hidden item"
            ),
            DBusMenuItem(
                None,
                id=0,
                item_type="separator",
                enabled=True,
                visible=True,
                label=""
            ),
            DBusMenuItem(
                None,
                id=0,
                item_type="",
                enabled=True,
                visible=True,
                label="Menu Item 2"
            )
        ]

        menu = PopupMenu.from_dbus_menu(
            self,
            items
        )

        menu.show(0, 0)
    """))
    assert success, msg

    layout = manager.c.internal_windows()[0]
    assert layout["name"] == "popupmenu"

    # There should only be 3 items as one item has visible=False
    assert len(layout["controls"]) == 3

    # Menu height is calculated as follows:
    #  Number of rows * fontsize (default is 12)
    #  Number of rows is 2 for text and 1 for separator
    #  So, we have 5 rows x 12 = 60
    assert layout["height"] == 60

    # Check that correct menu items are created
    item_types = [item["name"] for item in layout["controls"]]
    assert item_types == ["popupmenuitem", "popupmenuseparator", "popupmenuitem"]
