# Copyright (C) 2016, zordsdavini
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

from .dmenu import Dmenu


class GroupList(Dmenu):
    """
    Give vertical list of all groups in dmenu. Switch to selected.
    Inspired by WindowList http://docs.qtile.org/en/latest/_modules/libqtile/extension/window_list.html
    """

    defaults = [
        ("item_format", "{id}: {group}", "the format for the menu items"),
    ]

    def __init__(self, **config):
        Dmenu.__init__(self, **config)
        self.add_defaults(GroupList.defaults)

    def _configure(self, qtile):
        Dmenu._configure(self, qtile)

    def list_groups(self):
        id = 0
        self.item_to_group = {}

        for group in self.qtile.groups:
            item = self.item_format.format(
                id=id, group=group.label or group.name
            )
            self.item_to_group[item] = group
            id += 1

    def run(self):
        self.list_groups()
        out = super(GroupList, self).run(items=self.item_to_group.keys())

        try:
            sout = out.rstrip('\n')
        except AttributeError:
            # out is not a string (for example it's a Popen object returned
            # by super(GroupList, self).run() when there are no menu items to
            # list
            return

        try:
            group = self.item_to_group[sout]
        except KeyError:
            # The selected group got closed while the menu was open?
            return

        # @TODO implement moving to different screen
        screen = self.qtile.currentScreen
        screen.setGroup(group)
