import libpry
import libqtile.utils as utils


class utranslateMasks(libpry.AutoTree):
    def test_one(self):
        assert utils.translateMasks(["shift", "control"])
        assert utils.translateMasks([]) == 0


tests = [
    utranslateMasks()
]

