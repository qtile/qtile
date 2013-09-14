"""
Class defining a kind of constants by a string name 
"""

class Obj:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

# Several predefined constants related to object size adaptation 
# e.g.: bar, pane, widgets ...
STRETCH = Obj("STRETCH")
CALCULATED = Obj("CALCULATED")
STATIC = Obj("STATIC")

UNSPECIFIED = Obj("UNSPECIFIED")

