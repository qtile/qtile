import operator
from Xlib import X
import manager

_modmasks = {
    "shift":    X.ShiftMask,
    "lock":     X.LockMask,
    "control":  X.ControlMask,
    "mod1":     X.Mod1Mask,
    "mod2":     X.Mod2Mask,
    "mod3":     X.Mod3Mask,
    "mod4":     X.Mod4Mask,
    "mod5":     X.Mod5Mask,
}

def translateMasks(modifiers):
    """
        Translate a modifier mask specified as a list of strings into an or-ed 
        bit representation.
    """
    masks = []
    for i in modifiers:
        try:
            masks.append(_modmasks[i])
        except KeyError:
            raise manager.QTileError("Unknown modifier: %s"%i)
    return reduce(operator.or_, masks) if masks else 0


