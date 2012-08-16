import time
import cStringIO
import libpry
import libqtile.manager
import libqtile.hook
import utils


class uHook(libpry.AutoTree):
    def tearDown(self):
        libqtile.hook.clear()

    def setUpAll(self):
        class Dummy:
            pass
        dummy = Dummy()
        io = cStringIO.StringIO()
        dummy.log = libqtile.manager.Log(5, io)
        libqtile.hook.init(dummy)

    def test_basic(self):
        self.testVal = None

        def test(x):
            self.testVal = x

        libpry.raises("unknown event", libqtile.hook.fire, "unkown")
        libqtile.manager.hook.subscribe.group_window_add(test)
        libqtile.manager.hook.fire("group_window_add", 1)
        assert self.testVal == 1

        assert libqtile.manager.hook.subscriptions
        libqtile.manager.hook.clear()
        assert not libqtile.manager.hook.subscriptions

    def test_unsubscribe(self):
        self.testVal = None

        def test(x):
            self.testVal = x

        libqtile.manager.hook.subscribe.group_window_add(test)
        libqtile.manager.hook.fire("group_window_add", 3)
        assert self.testVal == 3

        libqtile.manager.hook.unsubscribe.group_window_add(test)
        libqtile.manager.hook.fire("group_window_add", 4)
        assert self.testVal == 3

        libqtile.manager.hook.clear()
        assert not libqtile.manager.hook.subscriptions


tests = [
    uHook(),
]
