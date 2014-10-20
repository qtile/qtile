from libqtile import confreader
from nose.tools import raises

import os
tests_dir = os.path.dirname(os.path.realpath(__file__))

@raises(confreader.ConfigError)
def test_syntaxerr():
    confreader.File(os.path.join(tests_dir, "configs", "syntaxerr.py"))


def test_basic():
    f = confreader.File(os.path.join(tests_dir, "configs", "basic.py"))
    assert f.keys

def test_falls_back():
    f = confreader.File(os.path.join(tests_dir, "configs", "basic.py"))

    # We just care that it has a default, we don't actually care what the
    # default is; don't assert anything at all about the default in case
    # someone changes it down the road.
    assert hasattr(f, "follow_mouse_focus")
