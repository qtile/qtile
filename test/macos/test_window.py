def test_macos_window_mapping(mmanager):
    # mmanager is our TestManager with MacOSBackend

    # Spawn a window
    mmanager.backend.test_window("test-one")

    # Wait for qtile to manage it
    # Note: our AXObserver should trigger self.qtile.manage(win)

    # Check if window is managed
    # We might need a small delay or retry because AX is async
    import time

    for _ in range(50):
        if len(mmanager.c.windows()) > 0:
            break
        time.sleep(0.1)

    windows = mmanager.c.windows()
    assert len(windows) > 0

    # Check window info
    # Find our window by name (it might be mixed with other open windows if not careful)
    # But in a clean test environment it should be fine.
    our_win = None
    for w in windows:
        if w["name"] == "test-one":
            our_win = w
            break

    assert our_win is not None
    assert our_win["name"] == "test-one"
    assert "com.apple." not in str(our_win["wm_class"])  # It should have our app name or similar
