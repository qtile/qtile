import libpry
from libqtile import confreader, manager


class uConfig(libpry.AutoTree):
    def test_syntaxerr(self):
        libpry.raises("invalid syntax", confreader.File, "configs/syntaxerr.py")

    def test_basic(self):
        f = confreader.File("configs/basic.py")
        assert f.keys
        assert f.themedir == "configs/themes"
        

tests = [
    uConfig()
]
