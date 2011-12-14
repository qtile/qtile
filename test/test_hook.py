import time
import cStringIO
import libqtile.manager
import libqtile.hook
from nose.tools import with_setup, raises


class TestCall(object):
    def __init__(self, val):
        self.val = val

    def __call__(self, val):
        self.val = val


def teardown():
    libqtile.hook.clear()


def setup():
    class Dummy:
        pass
    dummy = Dummy()
    io = cStringIO.StringIO()
    dummy.log = libqtile.manager.Log(5, io)
    libqtile.hook.init(dummy)


@raises(libqtile.manager.QtileError)
def test_unknown():
    libqtile.hook.fire("unkown")


@with_setup(setup, teardown)
def test_basic():
    test = TestCall(0)
    libqtile.manager.hook.subscribe.group_window_add(test)
    libqtile.manager.hook.fire("group_window_add", 8)
    assert test.val == 8

    assert libqtile.manager.hook.subscriptions
    libqtile.manager.hook.clear()
    assert not libqtile.manager.hook.subscriptions


@with_setup(setup, teardown)
def test_unsubscribe():
    test = TestCall(0)

    libqtile.manager.hook.subscribe.group_window_add(test)
    libqtile.manager.hook.fire("group_window_add", 3)
    assert test.val == 3

    libqtile.manager.hook.unsubscribe.group_window_add(test)
    libqtile.manager.hook.fire("group_window_add", 4)
    assert test.val == 3

    libqtile.manager.hook.clear()
    assert not libqtile.manager.hook.subscriptions
