from nose.tools import with_setup, raises
import cStringIO
import libqtile.hook
import libqtile.manager

# TODO: more tests required.
# 1. Check all hooks that can be fired


def setup_module():
    class Dummy:
        pass

    dummy = Dummy()
    io = cStringIO.StringIO()
    dummy.log = libqtile.manager.Log(5, io)
    libqtile.hook.init(dummy)


def teardown_func():
    libqtile.hook.clear()


@raises(libqtile.manager.QtileError)
def test_firing_unknown_event():
    libqtile.hook.fire("unknown")


@with_setup(None, teardown_func)
def test_subscriber_called():
    test_list = []

    def test(list):
        list.append(1)

    libqtile.manager.hook.subscribe.group_window_add(test)
    libqtile.manager.hook.fire("group_window_add", test_list)
    assert len(test_list) == 1
    assert 1 in test_list


@with_setup(None, teardown_func)
def test_subscriber_addition_removal():

    def test(list):
        pass

    libqtile.manager.hook.subscribe.group_window_add(test)
    assert libqtile.manager.hook.subscriptions
    libqtile.manager.hook.clear()
    assert not libqtile.manager.hook.subscriptions


@with_setup(None, teardown_func)
def test_unsubscribe():
    test_list = []

    def test(list):
        list.append(len(list) + 1)

    libqtile.manager.hook.subscribe.group_window_add(test)
    libqtile.manager.hook.fire("group_window_add", test_list)
    libqtile.manager.hook.unsubscribe.group_window_add(test)
    libqtile.manager.hook.fire("group_window_add", test_list)
    assert len(test_list) == 1
    assert 1 in test_list
