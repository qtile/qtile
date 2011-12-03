from libqtile import confreader, manager
from nose.tools import raises


@raises(confreader.ConfigError)
def test_syntaxerr():
    confreader.File('configs/syntaxerr.py')


def test_basic():
    f = confreader.File("configs/basic.py")
    assert f.keys
