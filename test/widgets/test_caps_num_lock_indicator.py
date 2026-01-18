from libqtile.widget import caps_num_lock_indicator


def test_cnli():
    widget = caps_num_lock_indicator.CapsNumLockIndicator()
    raw = """Keyboard Control:
  auto repeat:  on    key click percent:  0    LED mask:  00000002
  XKB indicators:
    00: Caps Lock:   off    01: Num Lock:    on     02: Scroll Lock: off
    03: Compose:     off    04: Kana:        off    05: Sleep:       off
"""
    text = widget.parse(raw)
    assert text == "Caps off Num on"


def test_cnli_caps_on():
    widget = caps_num_lock_indicator.CapsNumLockIndicator()
    raw = """Keyboard Control:
  auto repeat:  on    key click percent:  0    LED mask:  00000002
  XKB indicators:
    00: Caps Lock:   on     01: Num Lock:    on     02: Scroll Lock: off
    03: Compose:     off    04: Kana:        off    05: Sleep:       off
"""
    text = widget.parse(raw)
    assert text == "Caps on Num on"
