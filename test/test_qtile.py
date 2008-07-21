import os, time, cStringIO
import libpry
import libqtile
import utils

class MaxConfig(libqtile.config.Config):
    groups = ["a", "b", "c", "d"]
    layouts = [libqtile.layout.Max()]
    keys = [
        libqtile.Key(["control"], "k", libqtile.command.Call("max_next")),
        libqtile.Key(["control"], "j", libqtile.command.Call("max_previous")),
    ]
    screens = []


class uMultiScreen(utils.QTileTests):
    config = MaxConfig()
    def test_to_screen(self):
        assert self.c.current_screen() == 0
        self.c.to_screen(1)
        assert self.c.current_screen() == 1
        self.testWindow("one")
        self.c.to_screen(0)
        self.testWindow("two")

        ga = self.c.groupinfo("a")
        assert ga["clients"] == ["two"]

        gb = self.c.groupinfo("b")
        assert gb["clients"] == ["one"]


class uCommon(utils.QTileTests):
    """
        We don't care if these tests run in a Xinerama or non-Xinerama X.
    """
    config = MaxConfig()
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
        assert self.c.groupinfo("a")["focus"] == "two"
        self.c.simulate_keypress(["control"], "j")
        assert self.c.groupinfo("a")["focus"] == "one"

    def test_spawn(self):
        assert self.c.spawn("true") == None

    def test_kill(self):
        self.testWindow("one")
        self.testwindows = []
        self.c.kill()
        self.c.sync()
        for i in range(20):
            if self.c.clientcount() == 0:
                break
            time.sleep(0.1)
        else:
            raise AssertionError("Window did not die...")

    def test_regression_groupswitch(self):
        self.c.pullgroup("c")
        self.c.pullgroup("d")
        assert self.c.groupinfo("c")["screen"] == None

class uQTile(utils.QTileTests):
    """
        These tests should run in both Xinerama and non-Xinerama modes.
    """
    config = MaxConfig()
    def test_mapRequest(self):
        self.testWindow("one")
        info = self.c.groupinfo("a")
        assert "one" in info["clients"]
        assert info["focus"] == "one"

        self.testWindow("two")
        info = self.c.groupinfo("a")
        assert "two" in info["clients"]
        assert info["focus"] == "two"

    def test_unmap(self):
        one = self.testWindow("one")
        two = self.testWindow("two")
        three = self.testWindow("three")
        info = self.c.groupinfo("a")
        assert info["focus"] == "three"

        assert self.c.clientcount() == 3
        self.kill(three)

        assert self.c.clientcount() == 2
        info = self.c.groupinfo("a")
        assert info["focus"] == "two"

        self.kill(two)
        assert self.c.clientcount() == 1
        info = self.c.groupinfo("a")
        assert info["focus"] == "one"

        self.kill(one)
        assert self.c.clientcount() == 0
        info = self.c.groupinfo("a")
        assert info["focus"] == None

    def test_setgroup(self):
        self.testWindow("one")
        libpry.raises("No such group", self.c.pullgroup, "nonexistent")
        self.c.pullgroup("b")
        if len(self.c.screens()) == 1:
            assert self.c.groupinfo("a")["screen"] == None
        else:
            assert self.c.groupinfo("a")["screen"] == 1
        assert self.c.groupinfo("b")["screen"] == 0
        self.c.pullgroup("c")
        assert self.c.groupinfo("c")["screen"] == 0

    def test_unmap_noscreen(self):
        self.testWindow("one")
        pid = self.testWindow("two")
        assert self.c.clientcount() == 2
        self.c.pullgroup("c")
        assert self.c.clientcount() == 2
        self.kill(pid)
        assert self.c.clientcount() == 1
        assert self.c.groupinfo("a")["focus"] == "one"

    def test_restart(self):
        self.testWindow("one")
        self.testWindow("two")
        self.c.restart()

        #assert self.c.clientcount() == 2


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
        uCommon(),
        uQTile()
    ],
    uKey(),
    uLog(),
    uScreenDimensions()
]
