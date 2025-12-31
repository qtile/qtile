from libqtile.config import Screen


def test_screen_equality_bad_serial():
    # Two screens with different geometry but SAME bad serial
    s1 = Screen(x=0, y=0, width=1920, height=1080, serial="000000000000")
    s2 = Screen(x=1920, y=0, width=1920, height=1080, serial="000000000000")

    # Should NOT be equal because we ignore the bad serial and fall back to geometry
    assert s1 != s2

    # Verify hash is distinct
    assert hash(s1) != hash(s2)


def test_screen_equality_good_serial():
    # Two screens with different geometry but same GOOD serial
    # This implies they are physically the same monitor (moved?), so they SHOULD be equal
    # (This preserves the feature for valid hardware)
    s1 = Screen(x=0, y=0, width=1920, height=1080, serial="serial123")
    s2 = Screen(x=1920, y=0, width=1920, height=1080, serial="serial123")

    assert s1 == s2
