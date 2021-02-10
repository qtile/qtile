from libqtile.bar import Bar
from libqtile.widget import CheckUpdates


def no_op(*args, **kwargs):
    pass


class FakeWindow:
    class _NestedWindow:
        wid = 10
    window = _NestedWindow()


class FakeQtile:
    def __init__(self):
        self.call_soon = no_op
        self.register_widget = no_op


wrong_distro = "Barch"
good_distro = "Arch"
cmd_0_line = "export toto"   # quick "monkeypatch" simulating 0 output, ie 0 update
cmd_1_line = "echo toto"     # quick "monkeypatch" simulating 1 output, ie 1 update
nus = "No Update Avalaible"


def test_unknown_distro():
    """ test an unknown distribution """
    cu = CheckUpdates(distro=wrong_distro)
    text = cu.poll()
    assert text == "N/A"


def test_update_available():
    """ test output with update (check number of updates and color) """
    cu2 = CheckUpdates(distro=good_distro,
                       custom_command=cmd_1_line,
                       colour_have_updates="#123456"
                       )
    fakeqtile = FakeQtile()
    cu2.qtile = fakeqtile
    fakebar = Bar([cu2], 24)
    fakebar.window = FakeWindow()
    fakebar.width = 10
    fakebar.height = 10
    fakebar.draw = no_op
    cu2._configure(fakeqtile, fakebar)
    text = cu2.poll()
    assert text == "Updates: 1"
    assert cu2.layout.colour == cu2.colour_have_updates


def test_no_update_available_without_no_update_string():
    """ test output with no update (without dedicated string nor color) """
    cu3 = CheckUpdates(distro=good_distro, custom_command=cmd_0_line)
    fakeqtile = FakeQtile()
    cu3.qtile = fakeqtile
    fakebar = Bar([cu3], 24)
    fakebar.window = FakeWindow()
    fakebar.width = 10
    fakebar.height = 10
    fakebar.draw = no_op
    cu3._configure(fakeqtile, fakebar)
    text = cu3.poll()
    assert text == ""


def test_no_update_available_with_no_update_string_and_color_no_updates():
    """ test output with no update (with dedicated string and color) """
    cu4 = CheckUpdates(distro=good_distro,
                       custom_command=cmd_0_line,
                       no_update_string=nus,
                       colour_no_updates="#654321"
                       )
    fakeqtile = FakeQtile()
    cu4.qtile = fakeqtile
    fakebar = Bar([cu4], 24)
    fakebar.window = FakeWindow()
    fakebar.width = 10
    fakebar.height = 10
    fakebar.draw = no_op
    cu4._configure(fakeqtile, fakebar)
    text = cu4.poll()
    assert text == nus
    assert cu4.layout.colour == cu4.colour_no_updates
