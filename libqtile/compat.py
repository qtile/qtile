"""
Minimal compatibility layer for dealing with Python 2/3 compatibility
"""

import sys

PY3 = sys.version_info[0] > 2

if PY3:
    # Moved imports
    from subprocess import getoutput
    from gi.repository import GObject as gobject
    from functools import reduce
    from sys import maxsize as maxint
    from io import StringIO, BytesIO

    # Renamed objects
    unicode = string_type = str
    unichr = chr
    input = input
else:
    from commands import getoutput
    import gobject
    reduce = reduce
    maxint = sys.maxint
    from cStringIO import StringIO
    BytesIO = StringIO

    string_type = basestring
    unicode = unicode
    unichr = unichr
    input = raw_input
