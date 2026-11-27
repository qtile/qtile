import xcffib.keysymdef
import xcffib.xf86keysym

keysyms = {}
for _name, _value in vars(xcffib.keysymdef).items():
    if _name.startswith("XK_"):
        keysyms[_name[len("XK_") :]] = _value
for _name, _value in vars(xcffib.xf86keysym).items():
    if _name.startswith("XF86XK_"):
        keysyms["XF86" + _name[len("XF86XK_") :]] = _value

keysyms = {k.lower(): v for k, v in keysyms.items()}
