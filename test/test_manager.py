import os, time, cStringIO, pprint
import libpry
import libqtile
import utils

class TestConfig(libqtile.config.Config):
    groups = ["a", "b", "c", "d"]
    layouts = [
                libqtile.layout.Max(),
                libqtile.layout.Stack(2)
            ]
    keys = [
        libqtile.Key(["control"], "k", libqtile.command.Call("max_next")),
        libqtile.Key(["control"], "j", libqtile.command.Call("max_previous")),
    ]
    screens = [libqtile.Screen()]


class uMultiScreen(utils.QTileTests):
    config = TestConfig()
    def test_to_screen(self):
        assert self.c.current_screen() == 0
        self.c.to_screen(1)
        assert self.c.current_screen() == 1
        self.testWindow("one")
        self.c.to_screen(0)
        self.testWindow("two")

        ga = self.c.groups()["a"]
        assert ga["clients"] == ["two"]

        gb = self.c.groups()["b"]
        assert gb["clients"] == ["one"]


class uSingle(utils.QTileTests):
    """
        We don't care if these tests run in a Xinerama or non-Xinerama X, and
        they only have to run under one of the two.
    """
    config = TestConfig()
    def test_events(self):
        assert self.c.status() == "OK"

    def test_report(self):
        p = os.path.join(self["tmpdir"], "crashreport")
        self.c.report("msg", p)
        assert os.path.isfile(p)

    def test_keypress(self):
        self.testWindow("one")
        self.testWindow("two")
        v = self.c.simulate_keypress(["unknown"], "j")
        assert v.startswith("Unknown modifier")
        assert self.c.groups()["a"]["focus"] == "two"
        self.c.simulate_keypress(["control"], "j")
        assert self.c.groups()["a"]["focus"] == "one"

    def test_spawn(self):
        assert self.c.spawn("true") == None

    def test_kill(self):
        self.testWindow("one")
        self.testwindows = []
        self.c.kill()
        self.c.sync()
        for i in range(20):
            if len(self.c.clients()) == 0:
                break
            time.sleep(0.1)
        else:
            raise AssertionError("Window did not die...")

    def test_regression_groupswitch(self):
        self.c.pullgroup("c")
        self.c.pullgroup("d")
        assert self.c.groups()["c"]["screen"] == None

    def test_nextlayout(self):
        self.testWindow("one")
        self.testWindow("two")
        assert self.c.groups()["a"]["layout"] == "max"
        self.c.nextlayout()
        assert self.c.groups()["a"]["layout"] == "stack"
        self.c.nextlayout()
        assert self.c.groups()["a"]["layout"] == "max"

    def test_log_clear(self):
        self.testWindow("one")
        self.c.log_clear()
        assert len(self.c.log()) == 1

    def test_log_length(self):
        self.c.log_setlength(5)
        assert self.c.log_getlength() == 5

    def test_inspect(self):
        self.testWindow("one")
        pprint.pprint(self.c.inspect())


class uQTile(utils.QTileTests):
    """
        These tests should run in both Xinerama and non-Xinerama modes.
    """
    config = TestConfig()
    def test_mapRequest(self):
        self.testWindow("one")
        info = self.c.groups()["a"]
        assert "one" in info["clients"]
        assert info["focus"] == "one"

        self.testWindow("two")
        info = self.c.groups()["a"]
        assert "two" in info["clients"]
        assert info["focus"] == "two"

    def test_unmap(self):
        one = self.testWindow("one")
        two = self.testWindow("two")
        three = self.testWindow("three")
        info = self.c.groups()["a"]
        assert info["focus"] == "three"

        assert len(self.c.clients()) == 3
        self.kill(three)

        assert len(self.c.clients()) == 2
        info = self.c.groups()["a"]
        assert info["focus"] == "two"

        self.kill(two)
        assert len(self.c.clients()) == 1
        info = self.c.groups()["a"]
        assert info["focus"] == "one"

        self.kill(one)
        assert len(self.c.clients()) == 0
        info = self.c.groups()["a"]
        assert info["focus"] == None

    def test_setgroup(self):
        self.testWindow("one")
        libpry.raises("No such group", self.c.pullgroup, "nonexistent")
        self.c.pullgroup("b")
        if len(self.c.screens()) == 1:
            assert self.c.groups()["a"]["screen"] == None
        else:
            assert self.c.groups()["a"]["screen"] == 1
        assert self.c.groups()["b"]["screen"] == 0
        self.c.pullgroup("c")
        assert self.c.groups()["c"]["screen"] == 0

    def test_unmap_noscreen(self):
        self.testWindow("one")
        pid = self.testWindow("two")
        assert len(self.c.clients()) == 2
        self.c.pullgroup("c")
        assert len(self.c.clients()) == 2
        self.kill(pid)
        assert len(self.c.clients()) == 1
        assert self.c.groups()["a"]["focus"] == "one"

    def test_layoutinfo(self):
        self.testWindow("one")
        self.testWindow("two")
        assert self.c.layoutinfo()["group"] == "a"
        d = self.c.layoutinfo("b", 0)
        assert d["group"] == "b"
        libpry.raises("invalid layout", self.c.layoutinfo, "b", 99)
        libpry.raises("no such group", self.c.layoutinfo, "nonexistent", 0)

    def test_restart(self):
        self.testWindow("one")
        self.testWindow("two")
        self.c.restart()

        #assert len(self.c.clients()) == 2


class uKey(libpry.AutoTree):
    def test_init(self):
        libpry.raises(
            "unknown key",
            libqtile.Key,
            [], "unknown", libqtile.command.Call("foo")
        )
        libpry.raises(
            "unknown modifier",
            libqtile.Key,
            ["unknown"], "x", libqtile.command.Call("foo")
        )


class uLog(libpry.AutoTree):
    def test_all(self):
        io = cStringIO.StringIO()
        l = libqtile.Log(5, io)
        for i in range(10):
            l.add(i)
        assert len(l.log) == 5
        assert l.log[0] == 5
        assert l.log[4] == 9

        l.write(io, "\t")
        assert "\t5" in io.getvalue()
        l.clear()
        assert not l.log

        l.setLength(5)
        assert l.length == 5

    def test_setLength(self):
        io = cStringIO.StringIO()
        l = libqtile.Log(10, io)
        for i in range(10):
            l.add(i)
        assert l.length == 10
        assert len(l.log) == 10
        l.setLength(5)
        assert l.length == 5
        assert len(l.log) == 5
        assert l.log[-1] == 9
        


class TScreen(libqtile.Screen):
    def setGroup(self, x): pass


class uScreenDimensions(libpry.AutoTree):
    def test_dx(self):
        s = TScreen(left = libqtile.Gap(10))
        s._configure(0, 0, 0, 100, 100, None)
        assert s.dx == 10

    def test_dwidth(self):
        s = TScreen(left = libqtile.Gap(10))
        s._configure(0, 0, 0, 100, 100, None)
        assert s.dwidth == 90
        s.right = libqtile.Gap(10)
        assert s.dwidth == 80

    def test_dy(self):
        s = TScreen(top = libqtile.Gap(10))
        s._configure(0, 0, 0, 100, 100, None)
        assert s.dy == 10

    def test_dheight(self):
        s = TScreen(top = libqtile.Gap(10))
        s._configure(0, 0, 0, 100, 100, None)
        assert s.dheight == 90
        s.bottom = libqtile.Gap(10)
        assert s.dheight == 80


tests = [
    utils.XNest(xinerama=True), [
        uQTile(),
        uMultiScreen()
    ],
    utils.XNest(xinerama=False), [
        uSingle(),
        uQTile()
    ],
    uKey(),
    uLog(),
    uScreenDimensions()
]
