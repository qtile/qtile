from __future__ import absolute_import

import six

moves = [
    six.MovedModule("gobject", "gobject", "gi.repository.GObject"),
    six.MovedAttribute("getoutput", "commands", "subprocess"),
]

for m in moves:
    six.add_move(m)
