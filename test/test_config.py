import libpry
from libqtile import config


class uConfig(libpry.AutoTree):
    def test_syntaxerr(self):
        libpry.raises("invalid syntax", config.File, "configs/syntaxerr.py")

    def test_basic(self):
        f = config.File("configs/basic.py")


tests = [
    uConfig()
]
