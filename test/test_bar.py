import libpry
import libqtile, libqtile.config
import utils

class MaxConfig(libqtile.config.Config):
    groups = ["a", "b", "c", "d"]
    layouts = [libqtile.layout.Max()]
    bars = [
        libqtile.bar.Bar(0, [])
    ]


class uBarPositions(libpry.AutoTree):
    def test_foo(self):
        pass



tests = [
    uBarPositions()
]
