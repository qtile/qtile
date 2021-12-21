import libqtile.config
from libqtile.widget.check_updates import CheckUpdates, Popen  # noqa: F401
from test.widgets.conftest import FakeBar

wrong_distro = "Barch"
good_distro = "Arch"
cmd_0_line = "export toto"  # quick "monkeypatch" simulating 0 output, ie 0 update
cmd_1_line = "echo toto"  # quick "monkeypatch" simulating 1 output, ie 1 update
cmd_error = "false"
nus = "No Update Available"


# This class returns None when first polled (to simulate that the task is still running)
# and then 0 on the second call.
class MockPopen:
    def __init__(self, *args, **kwargs):
        self.call_count = 0

    def poll(self):
        if self.call_count == 0:
            self.call_count += 1
            return None
        return 0


# Bit of an ugly hack to replicate the above functionality but for a method.
class MockSpawn:
    call_count = 0

    @classmethod
    def call_process(cls, *args, **kwargs):
        if cls.call_count == 0:
            cls.call_count += 1
            return "Updates"
        return ""


def test_unknown_distro():
    """test an unknown distribution"""
    cu = CheckUpdates(distro=wrong_distro)
    text = cu.poll()
    assert text == "N/A"


def test_update_available(fake_qtile, fake_window):
    """test output with update (check number of updates and color)"""
    cu2 = CheckUpdates(
        distro=good_distro, custom_command=cmd_1_line, colour_have_updates="#123456"
    )
    fakebar = FakeBar([cu2], window=fake_window)
    cu2._configure(fake_qtile, fakebar)
    text = cu2.poll()
    assert text == "Updates: 1"
    assert cu2.layout.colour == cu2.colour_have_updates


def test_no_update_available_without_no_update_string(fake_qtile, fake_window):
    """test output with no update (without dedicated string nor color)"""
    cu3 = CheckUpdates(distro=good_distro, custom_command=cmd_0_line)
    fakebar = FakeBar([cu3], window=fake_window)
    cu3._configure(fake_qtile, fakebar)
    text = cu3.poll()
    assert text == ""


def test_no_update_available_with_no_update_string_and_color_no_updates(fake_qtile, fake_window):
    """test output with no update (with dedicated string and color)"""
    cu4 = CheckUpdates(
        distro=good_distro,
        custom_command=cmd_0_line,
        no_update_string=nus,
        colour_no_updates="#654321",
    )
    fakebar = FakeBar([cu4], window=fake_window)
    cu4._configure(fake_qtile, fakebar)
    text = cu4.poll()
    assert text == nus
    assert cu4.layout.colour == cu4.colour_no_updates


def test_update_available_with_restart_indicator(monkeypatch, fake_qtile, fake_window):
    """test output with no indicator where restart needed"""
    cu5 = CheckUpdates(
        distro=good_distro,
        custom_command=cmd_1_line,
        restart_indicator="*",
    )
    monkeypatch.setattr("os.path.exists", lambda x: True)
    fakebar = FakeBar([cu5], window=fake_window)
    cu5._configure(fake_qtile, fakebar)
    text = cu5.poll()
    assert text == "Updates: 1*"


def test_update_available_with_execute(manager_nospawn, minimal_conf_noscreen, monkeypatch):
    """test polling after executing command"""

    # Use monkeypatching to patch both Popen (for execute command) and call_process

    # This class returns None when first polled (to simulate that the task is still running)
    # and then 0 on the second call.
    class MockPopen:
        def __init__(self, *args, **kwargs):
            self.call_count = 0

        def poll(self):
            if self.call_count == 0:
                self.call_count += 1
                return None
            return 0

    # Bit of an ugly hack to replicate the above functionality but for a method.
    class MockSpawn:
        call_count = 0

        @classmethod
        def call_process(cls, *args, **kwargs):
            if cls.call_count == 0:
                cls.call_count += 1
                return "Updates"
            return ""

    cu6 = CheckUpdates(
        distro=good_distro,
        custom_command="dummy",
        execute="dummy",
        no_update_string=nus,
    )

    # Patch the necessary object
    monkeypatch.setattr(cu6, "call_process", MockSpawn.call_process)
    monkeypatch.setattr("libqtile.widget.check_updates.Popen", MockPopen)

    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=libqtile.bar.Bar([cu6], 10))]

    manager_nospawn.start(config)

    topbar = manager_nospawn.c.bar["top"]

    assert topbar.info()["widgets"][0]["text"] == "Updates: 1"

    # Clicking the widget triggers the execute command
    topbar.fake_button_press(0, "top", 0, 0, button=1)

    # The second time we poll the widget, the update process is complete
    # and there are no more updates
    _, result = manager_nospawn.c.widget["checkupdates"].eval("self.poll()")
    assert result == nus


def test_update_process_error(fake_qtile, fake_window):
    """test output where update check gives error"""
    cu7 = CheckUpdates(
        distro=good_distro,
        custom_command=cmd_error,
        no_update_string="ERROR",
    )
    fakebar = FakeBar([cu7], window=fake_window)
    cu7._configure(fake_qtile, fakebar)
    text = cu7.poll()
    assert text == "ERROR"


def test_line_truncations(fake_qtile, monkeypatch, fake_window):
    """test update count is reduced"""

    # Mock output to return 5 lines of text
    def mock_process(*args, **kwargs):
        return "1\n2\n3\n4\n5\n"

    # Fedora is set up to remove 1 from line count
    cu8 = CheckUpdates(distro="Fedora")

    monkeypatch.setattr(cu8, "call_process", mock_process)
    fakebar = FakeBar([cu8], window=fake_window)
    cu8._configure(fake_qtile, fakebar)
    text = cu8.poll()

    # Should have 4 updates
    assert text == "Updates: 4"
