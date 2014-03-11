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
