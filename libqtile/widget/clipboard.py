# vim: tabstop=4 shiftwidth=4 expandtab
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 roger
# Copyright (c) 2014 Adi Sieker
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

from . import base
from .. import bar, hook, xcbq


class Clipboard(base._TextBox):
    """
        Display current clipboard contents.
    """
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("selection", "CLIPBOARD",
            "the selection to display(CLIPBOARD or PRIMARY)"),
        ("max_width", 10, "maximum number of characters to display "
            "(None for all, useful when width is bar.STRETCH)"),
        ("timeout", 10,
            "Default timeout (seconds) for display text, None to keep forever"),
        ("blacklist", ["keepassx"],
            "list with blacklisted wm_class, sadly not every "
            "clipboard window sets them, keepassx does."
            "Clipboard contents from blacklisted wm_classes "
            "will be replaced by the value of ``blacklist_text``."),
        ("blacklist_text", "***********",
            "text to display when the wm_class is blacklisted")
    ]

    def __init__(self, width=bar.CALCULATED, **config):
        base._TextBox.__init__(self, "", width, **config)
        self.add_defaults(Clipboard.defaults)
        self.timeout_id = None

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        self.text = ""
        self.setup_hooks()

    def clear(self, *args):
        self.text = ""
        self.bar.draw()

    def is_blacklisted(self, owner_id):
        if not self.blacklist:
            return False

        if owner_id in self.qtile.windowMap:
            owner = self.qtile.windowMap[owner_id].window
        else:
            owner = xcbq.Window(self.qtile.conn, owner_id)

        owner_class = owner.get_wm_class()
        if owner_class:
            for wm_class in self.blacklist:
                if wm_class in owner_class:
                    return True

    def setup_hooks(self):
        def hook_change(name, selection):
            if name != self.selection:
                return

            if self.is_blacklisted(selection["owner"]):
                text = self.blacklist_text
            else:
                text = selection["selection"].replace("\n", " ")

                text = text.strip()
                if self.max_width is not None and len(text) > self.max_width:
                    text = text[:self.max_width] + "..."

            self.text = text

            if self.timeout_id:
                self.timeout_id.cancel()
                self.timeout_id = None

            if self.timeout:
                self.timeout_id = self.timeout_add(self.timeout, self.clear)
            self.bar.draw()

        def hook_notify(name, selection):
            if name != self.selection:
                return

            if self.timeout_id:
                self.timeout_id.cancel()
                self.timeout_id = None

            # only clear if don't change don't apply in .5 seconds
            self.timeout_id = self.timeout_add(.5, self.clear)

        hook.subscribe.selection_notify(hook_notify)
        hook.subscribe.selection_change(hook_change)
