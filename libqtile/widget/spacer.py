from .. import bar
import base

class Spacer(base._Widget):
    def __init__(self, width=bar.STRETCH, **attrs):
        base._Widget.__init__(self, width, **attrs)

    def draw(self):
        pass

